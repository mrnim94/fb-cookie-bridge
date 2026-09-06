"""Facebook group moderation operations using curl_cffi."""
from __future__ import annotations

import json
import logging
import re
from urllib.parse import urlencode

from .facebook import FacebookClient, RequestError, load_cookies

LOG = logging.getLogger(__name__)

RELAY_INTERNAL_FLAGS = {
    "__relay_internal__pv__FBReels_enable_view_dubbed_audio_type_gkrelayprovider": True,
    "__relay_internal__pv__GHLShouldChangeAdIdFieldNamerelayprovider": True,
    "__relay_internal__pv__GHLShouldChangeSponsoredDataFieldNamerelayprovider": True,
    "__relay_internal__pv__CometFeedStory_enable_reactor_facepilerelayprovider": False,
    "__relay_internal__pv__CometFeedStory_enable_social_bubblesrelayprovider": False,
    "__relay_internal__pv__CometFeedStory_enable_post_permalink_white_space_clickrelayprovider": False,
    "__relay_internal__pv__CometUFICommentActionLinksRewriteEnabledrelayprovider": True,
    "__relay_internal__pv__CometUFICommentAvatarStickerAnimatedImagerelayprovider": False,
    "__relay_internal__pv__IsWorkUserrelayprovider": False,
    "__relay_internal__pv__TestPilotShouldIncludeDemoAdUseCaserelayprovider": False,
    "__relay_internal__pv__FBReels_deprecate_short_form_video_context_gkrelayprovider": True,
    "__relay_internal__pv__CometFeedShareMedia_shouldPrefetchShareImagerelayprovider": False,
    "__relay_internal__pv__CometImmersivePhotoCanUserDisable3DMotionrelayprovider": False,
    "__relay_internal__pv__WorkCometIsEmployeeGKProviderrelayprovider": False,
    "__relay_internal__pv__IsMergQAPollsrelayprovider": False,
    "__relay_internal__pv__FBReelsMediaFooter_comet_enable_reels_ads_gkrelayprovider": True,
    "__relay_internal__pv__CometUFIReactionsEnableShortNamerelayprovider": False,
    "__relay_internal__pv__CometUFICommentAutoTranslationTyperelayprovider": "AUTO_TRANSLATE",
    "__relay_internal__pv__CometUFIShareActionMigrationrelayprovider": True,
    "__relay_internal__pv__CometUFISingleLineUFIrelayprovider": True,
    "__relay_internal__pv__relay_provider_comet_ufi_ssr_seo_deferrelayprovider": True,
    "__relay_internal__pv__CometUFI_dedicated_comment_routable_dialog_gkrelayprovider": True,
    "__relay_internal__pv__ReelsIFUCard_reelsIFULikeCountrelayprovider": False,
    "__relay_internal__pv__FBReelsIFUTileContent_reelsIFUPlayOnHoverrelayprovider": True,
    "__relay_internal__pv__GroupsCometGYSJFeedItemHeightrelayprovider": 206,
    "__relay_internal__pv__StoriesShouldEnablePhotosensitiveContentWarningrelayprovider": False,
    "__relay_internal__pv__ShouldEnableBakedInTextStoriesrelayprovider": False,
    "__relay_internal__pv__StoriesShouldIncludeFbNotesrelayprovider": True,
    "__relay_internal__pv__GroupsCometGroupChatLazyLoadLastMessageSnippetrelayprovider": False,
}


def extract_all_text(obj, acc=None):
    if acc is None:
        acc = []
    if isinstance(obj, dict):
        if "text" in obj and isinstance(obj["text"], str):
            t = obj["text"].strip()
            if len(t) > 3 and t not in ("Like", "Comment", "Share", "Pending"):
                acc.append(t)
        for k, v in obj.items():
            if k not in ("tracking", "debug_info"):
                extract_all_text(v, acc)
    elif isinstance(obj, list):
        for item in obj:
            extract_all_text(item, acc)
    return acc


def parse_moderation_response(body: str, action: str, group_id: str, returncode: int = 0) -> dict:
    result = {"status": "unknown", "action": action, "confirmed": False}
    if returncode:
        return dict(result, error="transport_error")
    body = body.strip()
    if body.startswith("for (;;);"):
        body = body[len("for (;;);"):].lstrip()
    decoder = json.JSONDecoder()
    documents = []
    try:
        while body:
            document, end = decoder.raw_decode(body)
            if not isinstance(document, dict):
                return dict(result, error="invalid_response")
            documents.append(document)
            body = body[end:].lstrip()
    except (ValueError, TypeError):
        return dict(result, error="invalid_response")

    errors = [e for d in documents for e in (d.get("errors") or []) if isinstance(e, dict)]
    if errors:
        return dict(result, status="error", error="graphql_error",
                    error_codes=[str(e.get("code", "unknown")) for e in errors])

    key = {"APPROVE": "group_approve_pending_story", "DECLINE": "group_content_remove"}.get(action)
    for document in documents:
        data = document.get("data")
        mutation = data.get(key) if isinstance(data, dict) and key else None
        group = mutation.get("group") if isinstance(mutation, dict) else None
        if isinstance(group, dict) and str(group.get("id")) == str(group_id):
            return dict(result, status="ok", confirmed=True)
    return dict(result, error="missing_mutation_confirmation")


class GroupsService:
    def __init__(self, client: FacebookClient):
        self.client = client

    def _get_dtsg_and_actor(self, session, group_id: str) -> tuple[str, str, str]:
        url = f"https://www.facebook.com/groups/{group_id}/pending_posts/"
        res = session.get(url, timeout=self.client.timeout_seconds)
        html = res.text
        dtsg_m = re.search(r"\"DTSGInitialData\",\[\],\{\"token\":\"([^\"]+)\"\}", html)
        dtsg = dtsg_m.group(1) if dtsg_m else ""
        user_m = re.search(r"\"USER_ID\":\"(\d+)\"", html) or re.search(r"\"actorID\":\"(\d+)\"", html)
        actor_id = user_m.group(1) if user_m else ""
        return dtsg, actor_id, html

    def get_pending_posts(self, group_id: str, max_pages: int = 20) -> list[dict]:
        with self.client._session() as session:
            dtsg, actor_id, html = self._get_dtsg_and_actor(session, group_id)
            if not dtsg:
                raise RequestError("failed_to_extract_dtsg_token")

            cursor_m = re.search(
                r"\"pending_posts_section_stories\":\{.*?\"page_info\":\{.*?\"end_cursor\":\"([^\"]+)\",\"has_next_page\":(true|false)",
                html
            )
            cursor = cursor_m.group(1) if cursor_m else ""
            has_next = (cursor_m.group(2) == "true") if cursor_m else False

            collected = []
            seen_pids = set()

            def add_node(nd):
                pid = nd.get("post_id")
                if not pid or pid in seen_pids:
                    return
                seen_pids.add(pid)
                fb = nd.get("feedback", {})
                owner = fb.get("owning_profile", {}) if fb else {}
                author = owner.get("name") if owner else "Unknown"
                author_id = owner.get("id") if owner else None
                node_id = nd.get("id")
                texts = list(dict.fromkeys(extract_all_text(nd)))
                main_text = sorted(texts, key=len, reverse=True)[0] if texts else ""
                nd_str = json.dumps(nd)
                img_matches = re.findall(r"https://scontent[^\"]+\.(?:jpg|png|webp)[^\"]*", nd_str)
                clean_imgs = list(dict.fromkeys([m.replace("\\/", "/") for m in img_matches]))[:4]
                collected.append({
                    "groupId": group_id,
                    "postId": pid,
                    "nodeId": node_id,
                    "postUrl": f"https://www.facebook.com/groups/{group_id}/pending_posts/",
                    "author": author,
                    "authorId": author_id,
                    "content": main_text,
                    "images": clean_imgs,
                    "creationTime": nd.get("creation_time")
                })

            scripts = re.findall(r"<script type=\"application/json\"[^>]*data-sjs>(.*?)</script>", html)
            def parse_edges(data):
                if isinstance(data, dict):
                    for k in ["pending_posts_section_stories", "pending_posts_search"]:
                        if k in data and isinstance(data[k], dict) and "edges" in data[k]:
                            for e in data[k]["edges"]:
                                if isinstance(e, dict) and "node" in e:
                                    add_node(e["node"])
                    for v in data.values():
                        parse_edges(v)
                elif isinstance(data, list):
                    for item in data:
                        parse_edges(item)

            for s in scripts:
                try:
                    parse_edges(json.loads(s))
                except Exception:
                    pass

            page = 0
            while has_next and cursor and page < max_pages:
                page += 1
                variables = {
                    "count": 5,
                    "cursor": cursor,
                    "feedLocation": "GROUP_PENDING",
                    "feedbackSource": 0,
                    "focusCommentID": None,
                    "hoistedPostID": None,
                    "pendingStoriesOrderBy": None,
                    "privacySelectorRenderLocation": "COMET_STREAM",
                    "referringStoryRenderLocation": None,
                    "renderLocation": "group_pending_queue",
                    "scale": 1,
                    "useDefaultActor": False,
                    "id": group_id,
                    **RELAY_INTERNAL_FLAGS
                }
                post_data = {
                    "av": actor_id,
                    "__user": actor_id,
                    "__a": "1",
                    "fb_dtsg": dtsg,
                    "fb_api_caller_class": "RelayModern",
                    "fb_api_req_friendly_name": "GroupsCometPendingPostsFeedPaginationQuery",
                    "variables": json.dumps(variables),
                    "doc_id": "27988529814106715"
                }
                p_res = session.post(
                    "https://www.facebook.com/api/graphql/",
                    headers={
                        "Content-Type": "application/x-www-form-urlencoded",
                        "Referer": f"https://www.facebook.com/groups/{group_id}/pending_posts/",
                    },
                    data=post_data,
                    timeout=self.client.timeout_seconds
                )

                new_cursor = None
                lines = [l for l in p_res.text.split("\n") if l.strip()]
                for l in lines:
                    try:
                        j = json.loads(l)
                        dn = j.get("data", {}).get("node", {})
                        sec = dn.get("pending_posts_section_stories", {})
                        for e in sec.get("edges", []):
                            nd = e.get("node", {})
                            if nd:
                                add_node(nd)
                        pi = sec.get("page_info", {})
                        if pi:
                            has_next = pi.get("has_next_page", False)
                            new_cursor = pi.get("end_cursor")
                    except Exception:
                        pass
                if not has_next or not new_cursor or new_cursor == cursor:
                    break
                cursor = new_cursor

            return collected

    def moderate_post(self, action: str, group_id: str, story_id: str, member_id: str | None = None) -> dict:
        action = action.upper()
        if action not in ("APPROVE", "DECLINE"):
            raise RequestError("invalid_action")

        with self.client._session() as session:
            dtsg, actor_id, _ = self._get_dtsg_and_actor(session, group_id)
            if not dtsg:
                raise RequestError("failed_to_extract_dtsg_token")

            if action == "DECLINE":
                variables = {
                    "currentSection": None,
                    "input": {
                        "client_mutation_id": "1",
                        "actor_id": actor_id,
                        "action_source": "GROUP_PENDING_POSTS",
                        "group_id": group_id,
                        "story_id": story_id
                    },
                    "memberID": member_id,
                    "scale": 1
                }
                doc_id = "28687144910873750"
                friendly_name = "GroupsCometDeclinePendingStoryMutation"
            else:
                variables = {
                    "currentSection": None,
                    "feedLocation": "GROUP",
                    "feedbackSource": 0,
                    "focusCommentID": None,
                    "groupID": group_id,
                    "hasHoistStories": False,
                    "hoistStories": [],
                    "hoistStoriesCount": 0,
                    "input": {
                        "action_source": "GROUP_PENDING_POSTS",
                        "actor_id": actor_id,
                        "client_mutation_id": "1",
                        "group_id": group_id,
                        "story_id": story_id,
                        "trust_author": False
                    },
                    "memberID": member_id,
                    "privacySelectorRenderLocation": "COMET_STREAM",
                    "referringStoryRenderLocation": None,
                    "renderLocation": "group",
                    "scale": 1,
                    "shouldDeferMainFeed": False,
                    "sortingSetting": "CHRONOLOGICAL",
                    "useDefaultActor": False,
                    **RELAY_INTERNAL_FLAGS
                }
                doc_id = "29313550778233686"
                friendly_name = "GroupsCometApprovePendingStoryMutation"

            post_data = {
                "av": actor_id,
                "__user": actor_id,
                "__a": "1",
                "fb_dtsg": dtsg,
                "fb_api_caller_class": "RelayModern",
                "fb_api_req_friendly_name": friendly_name,
                "variables": json.dumps(variables),
                "doc_id": doc_id
            }

            res = session.post(
                "https://www.facebook.com/api/graphql/",
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Referer": f"https://www.facebook.com/groups/{group_id}/pending_posts/",
                },
                data=post_data,
                timeout=self.client.timeout_seconds
            )
            return parse_moderation_response(res.text, action, group_id, 0)

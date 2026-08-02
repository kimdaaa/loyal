import requests

import constants


class Skins:
    def __init__(self, Requests):
        self.Requests = Requests
        self._skins_by_uuid = None  # lazily populated cache: {uuid_lowercase: display_name}
        self._weapons_by_name = None  # lazily populated cache: {displayName_lowercase: weapon_uuid}

    def _get_skins_dict(self):
        """Lazily bulk-fetches https://valorant-api.com/v1/weapons/skins on first call
        and caches uuid->displayName (lowercased uuid keys) for the process lifetime.
        On any failure, cache an empty dict so we don't retry every call and don't crash."""
        if self._skins_by_uuid is not None:
            return self._skins_by_uuid

        skins_by_uuid = {}
        try:
            response = requests.get("https://valorant-api.com/v1/weapons/skins")
            if response.ok:
                data = response.json().get("data") or []
                for skin in data:
                    uuid = skin.get("uuid")
                    display_name = skin.get("displayName")
                    if uuid and display_name:
                        skins_by_uuid[uuid.lower()] = display_name
        except Exception:
            skins_by_uuid = {}

        self._skins_by_uuid = skins_by_uuid
        return self._skins_by_uuid

    def _get_weapons_dict(self):
        """Lazily bulk-fetches https://valorant-api.com/v1/weapons on first call and
        caches displayName_lowercase -> weapon_uuid for the process lifetime.
        On any failure, cache an empty dict so we don't retry every call and don't crash."""
        if self._weapons_by_name is not None:
            return self._weapons_by_name

        weapons_by_name = {}
        try:
            response = requests.get("https://valorant-api.com/v1/weapons")
            if response.ok:
                data = response.json().get("data") or []
                for weapon in data:
                    uuid = weapon.get("uuid")
                    display_name = weapon.get("displayName")
                    if uuid and display_name:
                        weapons_by_name[display_name.lower()] = uuid
        except Exception:
            weapons_by_name = {}

        self._weapons_by_name = weapons_by_name
        return self._weapons_by_name

    def get_equipped_skin(self, puuid, weapon_name="Vandal"):
        """
        Fetches the player's loadout and resolves the display name of the skin
        currently equipped on `weapon_name`. Returns "N/A" if anything is
        missing/unresolvable. Never raises.
        """
        try:
            weapons_by_name = self._get_weapons_dict()
            if not weapons_by_name:
                return "N/A"

            weapon_uuid = weapons_by_name.get(weapon_name.lower())
            if not weapon_uuid:
                return "N/A"

            loadout = self.Requests.fetch(
                "pd", f"/personalization/v2/players/{puuid}/playerloadout", "get"
            )
            if not loadout:
                return "N/A"

            guns = loadout.get("Guns")
            if not guns:
                return "N/A"

            matched_gun = None
            for gun in guns:
                if gun.get("ID", "").lower() == weapon_uuid.lower():
                    matched_gun = gun
                    break

            if matched_gun is None:
                return "N/A"

            skin_uuid = matched_gun.get("SkinID")
            if not skin_uuid:
                return "N/A"

            skins_by_uuid = self._get_skins_dict()
            return skins_by_uuid.get(skin_uuid.lower(), "N/A")
        except Exception:
            return "N/A"

    def get_match_skins(self, match_id, state, weapon_name="Vandal"):
        """
        Fetches the bulk match-loadouts endpoint (glz), which returns every
        player's loadout in one call and -- unlike the per-player personalization
        endpoint -- isn't restricted to the local player. Returns
        {puuid: skin_display_name} for every player it could resolve. `state`
        must be "pregame" or "coregame". Never raises.
        """
        try:
            weapons_by_name = self._get_weapons_dict()
            weapon_uuid = weapons_by_name.get(weapon_name.lower())
            if not weapon_uuid:
                return {}

            endpoint_base = "pregame" if state == "pregame" else "core-game"
            loadouts_resp = self.Requests.fetch(
                "glz", f"/{endpoint_base}/v1/matches/{match_id}/loadouts", "get"
            )
            if not loadouts_resp:
                return {}

            skins_by_uuid = self._get_skins_dict()
            skin_socket_id = constants.sockets["skin"]

            result = {}
            for entry in loadouts_resp.get("Loadouts") or []:
                loadout = entry.get("Loadout") or entry
                puuid = entry.get("Subject") or loadout.get("Subject")
                if not puuid:
                    continue

                items = loadout.get("Items") or {}
                gun_item = next(
                    (item for item_id, item in items.items()
                     if str(item_id).lower() == weapon_uuid.lower()),
                    None,
                )
                if not gun_item:
                    continue

                sockets = gun_item.get("Sockets") or {}
                skin_socket = next(
                    (socket for socket_id, socket in sockets.items()
                     if str(socket_id).lower() == skin_socket_id.lower()),
                    None,
                )
                if not skin_socket:
                    continue

                skin_uuid = (skin_socket.get("Item") or {}).get("ID")
                if not skin_uuid:
                    continue

                result[puuid] = skins_by_uuid.get(skin_uuid.lower(), "N/A")

            return result
        except Exception:
            return {}

"""State adapters. ADAPTERS maps record_type → adapter instance."""

from titlivo.adapters.base import StateAdapter


class MaharashtraSatbara(StateAdapter):
    field_map_name = "mh_712"


class KarnatakaRTC(StateAdapter):
    field_map_name = "ka_rtc"


class Gujarat712(StateAdapter):
    field_map_name = "gj_712"


ADAPTERS: dict[str, StateAdapter] = {
    "mh_712": MaharashtraSatbara(),
    "ka_rtc": KarnatakaRTC(),
    "gj_712": Gujarat712(),
}
BY_STATE: dict[str, StateAdapter] = {a.state: a for a in ADAPTERS.values()}

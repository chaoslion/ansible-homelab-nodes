from urllib.parse import urlencode


class FilterModule:
    def filters(self):
        return {
            "homeassistant_name": self._homeassistant_name,
            "homeassistant_track": self._homeassistant_track,
            "homeassistant_track_multiple": self._homeassistant_track_multiple,
            "homeassistant_prometheus_query": lambda url, query: (
                f"{url}/api/v1/query?{urlencode({'query': query})}"
            ),
        }

    def _homeassistant_name(
        self,
        source,
        suffix: str | None = None,
        seperator: str | None = None,
    ):
        if seperator is None:
            seperator = "_"
        parts = ["homelab"]
        parts += [source.replace(" ", seperator).replace("-", seperator)]
        if suffix is not None:
            parts += [suffix]
        return seperator.join(parts)

    def _homeassistant_track(
        self,
        source,
        suffix: str,
    ):
        return (
            source,
            self._homeassistant_name(source, suffix=suffix),
        )

    def _homeassistant_track_multiple(
        self,
        source: str,
        suffixes: list[str],
    ):
        return (
            source,
            {
                suffix: self._homeassistant_name(source, suffix=suffix)
                for suffix in suffixes
            },
        )

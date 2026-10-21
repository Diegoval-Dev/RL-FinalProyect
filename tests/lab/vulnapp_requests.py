import httpx

from vulnapp.queries import EndpointSpec


def send(
    client: httpx.Client,
    spec: EndpointSpec,
    values: dict[str, str],
    location: str,
    headers: dict[str, str] | None = None,
):
    if location == "query":
        return client.get(spec.path, params=values, headers=headers)
    if location == "form":
        return client.post(spec.path, data=values, headers=headers)
    return client.post(spec.path, json=values, headers=headers)


def response_signature(response: httpx.Response) -> tuple[int, int]:
    rows = response.json().get("rows", []) if response.status_code == 200 else []
    return response.status_code, len(rows)

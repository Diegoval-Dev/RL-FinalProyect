"""Query templates of the vulnerable endpoints.

Values are concatenated into the SQL on purpose: this is the attack surface of the laboratory.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal

Location = Literal["query", "form", "json"]
Family = Literal["tautology", "union", "error", "boolean_blind", "stacked"]

LOCATIONS: tuple[Location, ...] = ("query", "form", "json")
FAMILIES: tuple[Family, ...] = ("tautology", "union", "error", "boolean_blind", "stacked")
BODY_LOCATIONS: tuple[Location, ...] = ("form", "json")


@dataclass(frozen=True)
class EndpointSpec:
    name: str
    path: str
    params: tuple[str, ...]
    locations: tuple[Location, ...]
    template: str
    benign_values: Mapping[str, str]
    families: tuple[Family, ...]
    returns_rows: bool = True

    @property
    def methods(self) -> tuple[str, ...]:
        methods = []
        if "query" in self.locations:
            methods.append("GET")
        if any(location in BODY_LOCATIONS for location in self.locations):
            methods.append("POST")
        return tuple(methods)


ENDPOINTS: tuple[EndpointSpec, ...] = (
    EndpointSpec(
        name="catalog",
        path="/catalog",
        params=("category",),
        locations=("query",),
        template=(
            "SELECT id, name, price, category FROM products "
            "WHERE category = '{category}' AND hidden = false ORDER BY id"
        ),
        benign_values={"category": "Libros"},
        families=("tautology", "union"),
    ),
    EndpointSpec(
        name="search",
        path="/search",
        params=("q",),
        locations=("query", "form", "json"),
        template=(
            "SELECT id, name, price FROM products "
            "WHERE name ILIKE '%{q}%' AND hidden = false ORDER BY id"
        ),
        benign_values={"q": "lap"},
        families=("union", "error", "boolean_blind"),
    ),
    EndpointSpec(
        name="product",
        path="/product",
        params=("id",),
        locations=("query",),
        template=(
            "SELECT id, name, price, description FROM products WHERE id = {id} AND hidden = false"
        ),
        benign_values={"id": "3"},
        families=("union", "error", "boolean_blind"),
    ),
    EndpointSpec(
        name="login",
        path="/login",
        params=("username", "password"),
        locations=("form", "json"),
        template=(
            "SELECT id, username, role FROM users "
            "WHERE username = '{username}' AND password = '{password}'"
        ),
        benign_values={"username": "ana", "password": "ana2024"},
        families=("tautology",),
    ),
    EndpointSpec(
        name="sort",
        path="/products/sort",
        params=("order",),
        locations=("query",),
        template="SELECT id, name, price FROM products WHERE hidden = false ORDER BY {order}",
        benign_values={"order": "price"},
        families=("error", "boolean_blind"),
    ),
    EndpointSpec(
        name="comments",
        path="/comments/add",
        params=("body",),
        locations=("form", "json"),
        template="INSERT INTO comments (product_id, author, body) VALUES (1, 'anon', '{body}')",
        benign_values={"body": "Excelente producto"},
        families=("stacked",),
        returns_rows=False,
    ),
    EndpointSpec(
        name="orders",
        path="/orders",
        params=("user_id",),
        locations=("query", "json"),
        template="SELECT id, user_id, total, status FROM orders WHERE user_id = {user_id}",
        benign_values={"user_id": "2"},
        families=("tautology", "union", "boolean_blind"),
    ),
    EndpointSpec(
        name="cart_add",
        path="/cart/add",
        params=("product_id", "qty"),
        locations=("form", "json"),
        template=(
            "INSERT INTO cart_items (user_id, product_id, qty) VALUES (2, {product_id}, {qty})"
        ),
        benign_values={"product_id": "4", "qty": "1"},
        families=("error", "stacked"),
        returns_rows=False,
    ),
)


def build_sql(spec: EndpointSpec, values: Mapping[str, str]) -> str:
    return spec.template.format_map(values)


def find_endpoint(name: str) -> EndpointSpec | None:
    return next((spec for spec in ENDPOINTS if spec.name == name), None)


def get_endpoint(name: str) -> EndpointSpec:
    return next(spec for spec in ENDPOINTS if spec.name == name)

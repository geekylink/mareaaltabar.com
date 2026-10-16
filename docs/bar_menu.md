# Marea Alta Surf Bar - Menu / Menú

> **This file seeded the database; the database is now the source of truth.**
> Everything below was transcribed into `backend/app/seed.py` and is published on
> the site at `/menu` (and in the homepage menu section). From here on, prices and
> drinks are edited in the **admin panel at `/admin/menu`**, not in this file —
> a change made here will not reach the site. Come back to this document only
> to record what the bar told you.

## Cerveza / Beer

| Español | English | Price / Precio |
| :--- | :--- | :--- |
| Club personal | Club Personal | $2.50 |
| Club grande | Club Large | $4.00 |
| Corona | Corona | $4.00 |
| Pilsener | Pilsener | $3.00 |
| Pilsener Light | Pilsener Light | $3.00 |
| Pilsener Lata | Pilsener Can | $1.50 (6x $7.00) |
| Pilsener Light Lata | Pilsener Light Can | $1.50 (6x $7.00) |

## Otras Bebidas / Other Drinks

| Español | English | Price / Precio |
| :--- | :--- | :--- |
| Cafe con Leche | Milk Coffee | $1.50 |
| Cafe | Coffee | $1.00 |
| Limonada | Lemonade | $1.50 |
| Jugo Natural | Natural Juice | $2.00 |
| Batidos | Milkshake | $2.50 |
| Cola, Sprite, Inca | Cola, Sprite, Inca | $1.00 |
| Agua | Water | $1.00 |

## Cigarrillo / Cigarette

| Español | English | Price / Precio |
| :--- | :--- | :--- |
| Elephant | Elephant | $0.25 / $4.00 paquete (packet) |
| Carnival | Carnival | $0.50 / $7.00 paquete (packet) |

## Cócteles / Cocktails

| English | Español | Price / Precio | Ingredients / Ingredientes |
| :--- | :--- | :--- | :--- |
| Cuba Libre | Cuba Libre | $4.00 | Rum, Coca-Cola, Lime juice, Ice / Ron, Coca-Cola, Jugo de limón, Hielo |

More to come. Each cocktail is a row in `menu_items` with its own price, its own
bilingual ingredient list and any number of promos under the price — add them
from `/admin/menu` as they are written up.

## How these tables map to the database

The multi-buy offers written inline above are **not** part of the price once
seeded. `$1.50 (6x $7.00)` becomes a price of `1.50` plus a promo row reading
`6x $7.00` / `6 por $7.00`, which is what the site renders under the price — so a
drink can carry several offers and each can be edited or removed on its own.

| Column here | Where it lives |
| :--- | :--- |
| Section heading | `menu_categories.name_en` / `name_es` |
| Español / English | `menu_items.name_es` / `name_en` |
| Price | `menu_items.price` — the bare amount, e.g. `1.50` |
| `(6x $7.00)`, `paquete` | `menu_item_promos.label_en` / `label_es` |
| Ingredients | `menu_items.ingredients_en` / `ingredients_es`, comma separated |

## Not in this file yet

The bar sells **wine and liquor**, and neither appears above. Both categories
exist in the database and are hidden from the site until something is added to
them, so the menu has somewhere for them to go.
"""
ShopFlow CLI — Sprint 1 命令行入口

用法：
    python -m shop.cli add --name "Widget" --price 9.99 --stock 100
    python -m shop.cli get --id 1
    python -m shop.cli list
    python -m shop.cli update --id 1 --price 12.99
    python -m shop.cli delete --id 1
    python -m shop.cli search --name "Widget"
"""

import argparse
import sys
from shop.product_store import ProductStore


def cmd_add(store: ProductStore, args):
    product = store.add(name=args.name, price=args.price, stock=args.stock)
    print(f"✓ Added: [{product.id}] {product.name} — ¥{product.price:.2f} (stock: {product.stock})")


def cmd_get(store: ProductStore, args):
    product = store.get_by_id(args.id)
    if product:
        print(f"[{product.id}] {product.name} — ¥{product.price:.2f} (stock: {product.stock})")
    else:
        print(f"✗ Product with id={args.id} not found", file=sys.stderr)
        sys.exit(1)


def cmd_list(store: ProductStore, args):
    products = store.list_all()
    if not products:
        print("No products found.")
        return
    print(f"{'ID':<6} {'Name':<30} {'Price':>10} {'Stock':>8}")
    print("-" * 58)
    for p in products:
        print(f"{p.id:<6} {p.name:<30} ¥{p.price:>9.2f} {p.stock:>8}")


def cmd_update(store: ProductStore, args):
    updates = {}
    if args.name:
        updates["name"] = args.name
    if args.price is not None:
        updates["price"] = args.price
    if args.stock is not None:
        updates["stock"] = args.stock

    if not updates:
        print("✗ No fields to update", file=sys.stderr)
        sys.exit(1)

    product = store.update(args.id, **updates)
    if product:
        print(f"✓ Updated: [{product.id}] {product.name} — ¥{product.price:.2f} (stock: {product.stock})")
    else:
        print(f"✗ Product with id={args.id} not found", file=sys.stderr)
        sys.exit(1)


def cmd_delete(store: ProductStore, args):
    if store.delete(args.id):
        print(f"✓ Deleted product id={args.id}")
    else:
        print(f"✗ Product with id={args.id} not found", file=sys.stderr)
        sys.exit(1)


def cmd_search(store: ProductStore, args):
    products = store.search_by_name(args.name)
    if not products:
        print(f"No products found matching '{args.name}'")
        return
    print(f"Found {len(products)} product(s):")
    for p in products:
        print(f"  [{p.id}] {p.name} — ¥{p.price:.2f} (stock: {p.stock})")


def main():
    parser = argparse.ArgumentParser(description="ShopFlow — 商品管理命令行工具")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # add
    add_parser = subparsers.add_parser("add", help="添加商品")
    add_parser.add_argument("--name", required=True, help="商品名称")
    add_parser.add_argument("--price", type=float, required=True, help="商品价格")
    add_parser.add_argument("--stock", type=int, default=0, help="库存数量")

    # get
    get_parser = subparsers.add_parser("get", help="按 ID 查询商品")
    get_parser.add_argument("--id", type=int, required=True, help="商品 ID")

    # list
    subparsers.add_parser("list", help="列出所有商品")

    # update
    update_parser = subparsers.add_parser("update", help="更新商品")
    update_parser.add_argument("--id", type=int, required=True, help="商品 ID")
    update_parser.add_argument("--name", help="新名称")
    update_parser.add_argument("--price", type=float, help="新价格")
    update_parser.add_argument("--stock", type=int, help="新库存")

    # delete
    delete_parser = subparsers.add_parser("delete", help="删除商品")
    delete_parser.add_argument("--id", type=int, required=True, help="商品 ID")

    # search
    search_parser = subparsers.add_parser("search", help="按名称搜索商品")
    search_parser.add_argument("--name", required=True, help="搜索关键词")

    args = parser.parse_args()
    store = ProductStore()

    commands = {
        "add": cmd_add,
        "get": cmd_get,
        "list": cmd_list,
        "update": cmd_update,
        "delete": cmd_delete,
        "search": cmd_search,
    }
    commands[args.command](store, args)


if __name__ == "__main__":
    main()

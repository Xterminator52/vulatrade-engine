import sqlite3
import datetime
import urllib.parse
import flet as ft

DB_FILE = "vulatrade.db"

# ==========================================
# DATABASE INITIALIZATION & OPERATIONS
# ==========================================
def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            cost_price REAL NOT NULL,
            selling_price REAL NOT NULL,
            stock INTEGER NOT NULL
        )
    """)
    # Seed default baseline convenience goods only if table is newly created and completely empty
    cursor.execute("SELECT COUNT(*) FROM products")
    if cursor.fetchone()[0] == 0:
        cursor.executemany("""
            INSERT INTO products (name, cost_price, selling_price, stock)
            VALUES (?, ?, ?, ?)
        """, [
            ("Coca-Cola 500ml", 22.00, 30.00, 10),
            ("Box of Matches", 1.00, 1.50, 25),
            ("Reboost Energy Drink", 10.00, 14.00, 12),
            ("Airtime Voucher R10", 9.00, 10.00, 5),
        ])
    conn.commit()
    conn.close()

def get_all_products():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()
    return rows

def add_product_to_db(name, cost, price, stock):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO products (name, cost_price, selling_price, stock)
        VALUES (?, ?, ?, ?)
    """, (name, cost, price, stock))
    conn.commit()
    conn.close()

def delete_product_from_db(product_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM products WHERE id = ?", (product_id,))
    conn.commit()
    conn.close()

def deduct_sold_stock(product_id, quantity=1):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE products 
        SET stock = stock - ? 
        WHERE id = ? AND stock >= ?
    """, (quantity, product_id, quantity))
    conn.commit()
    conn.close()


# ==========================================
# MAIN APPLICATION
# ==========================================
def main(page: ft.Page):
    page.title = "VulaTrade Engine"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 16
    page.scroll = ft.ScrollMode.ADAPTIVE

    init_db()

    # Active sale / receipt session items: list of dicts {id, name, price, qty}
    cart = []

    # ---------------- UI CONTROLS ----------------
    product_list_column = ft.Column(spacing=10)
    slip_items_column = ft.Column(spacing=6)
    
    slip_total_text = ft.Text("Total: R0.00", size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN_400)
    txt_cash_tendered = ft.TextField(
        label="Cash Tendered / Paid (R)",
        hint_text="e.g. 50.00",
        keyboard_type=ft.KeyboardType.NUMBER,
        dense=True,
        width=180
    )
    change_text = ft.Text("Change: R0.00", size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.AMBER_400)

    # Input fields for adding new inventory items
    txt_name = ft.TextField(label="Product Name", dense=True)
    txt_cost = ft.TextField(label="Cost Price (R)", keyboard_type=ft.KeyboardType.NUMBER, dense=True)
    txt_price = ft.TextField(label="Selling Price (R)", keyboard_type=ft.KeyboardType.NUMBER, dense=True)
    txt_stock = ft.TextField(label="Starting Stock", keyboard_type=ft.KeyboardType.NUMBER, dense=True)

    # ---------------- UTILITY HELPERS ----------------
    def show_toast(message: str, is_error: bool = False):
        page.snack_bar = ft.SnackBar(
            content=ft.Text(message, color=ft.Colors.WHITE),
            bgcolor=ft.Colors.RED_800 if is_error else ft.Colors.GREEN_800,
        )
        page.snack_bar.open = True
        page.update()

    def get_cart_total():
        return sum(item["price"] * item["qty"] for item in cart)

    def calculate_change(e=None):
        total = get_cart_total()
        tendered_str = txt_cash_tendered.value.strip() if txt_cash_tendered.value else ""
        if not tendered_str:
            change_text.value = "Change: R0.00"
            change_text.color = ft.Colors.AMBER_400
            page.update()
            return 0.0

        try:
            tendered = float(tendered_str)
            if tendered < total:
                shortage = total - tendered
                change_text.value = f"Short: R{shortage:.2f}"
                change_text.color = ft.Colors.RED_400
            else:
                change = tendered - total
                change_text.value = f"Change: R{change:.2f}"
                change_text.color = ft.Colors.GREEN_400
            page.update()
            return tendered
        except ValueError:
            change_text.value = "Invalid cash"
            change_text.color = ft.Colors.RED_400
            page.update()
            return 0.0

    txt_cash_tendered.on_change = calculate_change

    # ---------------- CART & SLIP LOGIC ----------------
    def refresh_slip_ui():
        slip_items_column.controls.clear()
        total = get_cart_total()

        if not cart:
            slip_items_column.controls.append(
                ft.Text("No items added to current slip.", italic=True, color=ft.Colors.GREY_500)
            )
        else:
            for item in cart:
                item_total = item["price"] * item["qty"]
                slip_items_column.controls.append(
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[
                            ft.Text(f"{item['name']} (x{item['qty']})", size=14),
                            ft.Text(f"R{item_total:.2f}", weight=ft.FontWeight.W_600),
                        ]
                    )
                )

        slip_total_text.value = f"Total: R{total:.2f}"
        calculate_change()
        page.update()

    def add_to_slip(item_id, name, price, stock):
        if stock <= 0:
            show_toast(f"'{name}' is out of stock!", is_error=True)
            return

        existing = next((i for i in cart if i["id"] == item_id), None)
        current_cart_qty = existing["qty"] if existing else 0

        if current_cart_qty >= stock:
            show_toast(f"Cannot add more '{name}'. Available stock reached ({stock}).", is_error=True)
            return

        if existing:
            existing["qty"] += 1
        else:
            cart.append({"id": item_id, "name": name, "price": price, "qty": 1})

        show_toast(f"Added '{name}' to digital slip")
        refresh_slip_ui()

    def clear_slip(e=None):
        cart.clear()
        txt_cash_tendered.value = ""
        refresh_slip_ui()
        show_toast("Slip cleared.")

    def finalize_and_share_slip(e):
        if not cart:
            show_toast("Cannot share an empty slip.", is_error=True)
            return

        total = get_cart_total()
        tendered_str = txt_cash_tendered.value.strip() if txt_cash_tendered.value else ""
        
        # Default to exact change if the field is left empty
        tendered = total
        if tendered_str:
            try:
                tendered = float(tendered_str)
            except ValueError:
                show_toast("Please enter a valid cash amount.", is_error=True)
                return

        if tendered < total:
            show_toast(f"Tendered amount (R{tendered:.2f}) is less than Total (R{total:.2f})!", is_error=True)
            return

        change = tendered - total

        # 1. Deduct stock from database
        for item in cart:
            deduct_sold_stock(item["id"], item["qty"])

        # 2. Build standard retail slip text
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        receipt = "🧾 *VULATRADE DIGITAL SLIP*\n"
        receipt += f"📅 Date: {now}\n"
        receipt += "------------------------------\n"
        for i in cart:
            receipt += f"• {i['name']} x{i['qty']} - R{i['price'] * i['qty']:.2f}\n"
        receipt += "------------------------------\n"
        receipt += f"💰 *TOTAL DUE: R{total:.2f}*\n"
        receipt += f"💵 *CASH PAID: R{tendered:.2f}*\n"
        receipt += f"🪙 *CHANGE: R{change:.2f}*\n"
        receipt += "------------------------------\n"
        receipt += "_Thank you for your support!_"

        # 3. Always copy to clipboard as guaranteed fallback
        page.set_clipboard(receipt)
        show_toast("Slip copied to clipboard! Opening WhatsApp...")

        # 4. Open WhatsApp
        encoded_text = urllib.parse.quote(receipt)
        whatsapp_url = f"https://wa.me/?text={encoded_text}"
        page.launch_url(whatsapp_url)

        # 5. Reset slip & refresh inventory
        cart.clear()
        txt_cash_tendered.value = ""
        refresh_slip_ui()
        refresh_product_list()

    # ---------------- INVENTORY UI & DELETE CONFIRMATION ----------------
    def confirm_delete_dialog(item_id, item_name):
        def delete_confirmed(e):
            delete_product_from_db(item_id)
            nonlocal_cart_filtered = [i for i in cart if i["id"] != item_id]
            cart.clear()
            cart.extend(nonlocal_cart_filtered)
            dialog.open = False
            page.update()
            refresh_product_list()
            refresh_slip_ui()
            show_toast(f"'{item_name}' removed from inventory.")

        def delete_cancelled(e):
            dialog.open = False
            page.update()

        dialog = ft.AlertDialog(
            title=ft.Text("Remove Item"),
            content=ft.Text(f"Are you sure you want to permanently delete '{item_name}'?"),
            actions=[
                ft.TextButton("Cancel", on_click=delete_cancelled),
                ft.TextButton(
                    "Delete", 
                    on_click=delete_confirmed, 
                    style=ft.ButtonStyle(color=ft.Colors.RED_400)
                ),
            ],
        )
        page.overlay.append(dialog)
        dialog.open = True
        page.update()

    def refresh_product_list():
        product_list_column.controls.clear()
        products = get_all_products()

        if not products:
            product_list_column.controls.append(
                ft.Container(
                    content=ft.Text("No products in inventory. Add your first item below.", italic=True),
                    padding=10
                )
            )
        else:
            for row in products:
                p_id = row["id"]
                p_name = row["name"]
                p_price = float(row["selling_price"])
                p_stock = int(row["stock"])
                is_out_of_stock = p_stock <= 0

                card = ft.Card(
                    elevation=2,
                    content=ft.Container(
                        padding=12,
                        content=ft.Row(
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            controls=[
                                ft.Column(
                                    controls=[
                                        ft.Text(
                                            p_name,
                                            size=16,
                                            weight=ft.FontWeight.BOLD,
                                            color=ft.Colors.GREY_500 if is_out_of_stock else ft.Colors.WHITE,
                                        ),
                                        ft.Text(f"Price: R{p_price:.2f}", size=13, color=ft.Colors.GREY_400),
                                        ft.Text(
                                            "OUT OF STOCK" if is_out_of_stock else f"Stock: {p_stock}",
                                            size=12,
                                            weight=ft.FontWeight.W_600,
                                            color=ft.Colors.RED_400 if is_out_of_stock else ft.Colors.GREEN_400,
                                        ),
                                    ],
                                    spacing=2,
                                ),
                                ft.Row(
                                    controls=[
                                        ft.ElevatedButton(
                                            text="Sold Out" if is_out_of_stock else "+ Slip",
                                            disabled=is_out_of_stock,
                                            on_click=lambda e, pid=p_id, pname=p_name, prc=p_price, stk=p_stock: add_to_slip(pid, pname, prc, stk),
                                            style=ft.ButtonStyle(
                                                bgcolor=ft.Colors.GREY_800 if is_out_of_stock else ft.Colors.TEAL_700,
                                                color=ft.Colors.GREY_600 if is_out_of_stock else ft.Colors.WHITE,
                                            ),
                                        ),
                                        ft.IconButton(
                                            icon=ft.Icons.DELETE_OUTLINE,
                                            icon_color=ft.Colors.RED_400,
                                            tooltip="Delete item",
                                            on_click=lambda e, pid=p_id, pname=p_name: confirm_delete_dialog(pid, pname),
                                        ),
                                    ],
                                    spacing=4,
                                ),
                            ],
                        ),
                    ),
                )
                product_list_column.controls.append(card)

        page.update()

    def handle_add_new_product(e):
        name = txt_name.value.strip() if txt_name.value else ""
        if not name:
            show_toast("Product name is required", is_error=True)
            return

        try:
            cost = float(txt_cost.value) if txt_cost.value else 0.0
            price = float(txt_price.value) if txt_price.value else 0.0
            stock = int(txt_stock.value) if txt_stock.value else 0
        except ValueError:
            show_toast("Please enter valid numbers for price and stock", is_error=True)
            return

        add_product_to_db(name, cost, price, stock)
        
        txt_name.value = ""
        txt_cost.value = ""
        txt_price.value = ""
        txt_stock.value = ""

        refresh_product_list()
        show_toast(f"'{name}' added to inventory!")

    # ---------------- MAIN LAYOUT ----------------
    page.add(
        ft.Row(
            controls=[
                ft.Icon(ft.Icons.STOREFRONT, color=ft.Colors.TEAL_400, size=28),
                ft.Text("VulaTrade Offline Engine", size=22, weight=ft.FontWeight.BOLD),
            ],
            alignment=ft.MainAxisAlignment.START,
        ),
        ft.Divider(),

        # SECTION 1: Active Digital Slip
        ft.Text("Active Till / Digital Slip", size=18, weight=ft.FontWeight.W_600),
        ft.Container(
            padding=12,
            border_radius=8,
            bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
            content=ft.Column(
                controls=[
                    slip_items_column,
                    ft.Divider(),
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[
                            slip_total_text,
                            ft.OutlinedButton("Clear Slip", on_click=clear_slip),
                        ],
                    ),
                    # Cash Tendered & Change Row
                    ft.Container(
                        padding=ft.padding.symmetric(vertical=6),
                        content=ft.Row(
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            controls=[
                                txt_cash_tendered,
                                change_text,
                            ]
                        )
                    ),
                    ft.Row(
                        alignment=ft.MainAxisAlignment.END,
                        controls=[
                            ft.ElevatedButton(
                                "Finish & Send Slip",
                                icon=ft.Icons.RECEIPT_LONG,
                                bgcolor=ft.Colors.GREEN_700,
                                color=ft.Colors.WHITE,
                                on_click=finalize_and_share_slip,
                            ),
                        ]
                    ),
                ]
            ),
        ),

        ft.Divider(),

        # SECTION 2: Inventory Catalog
        ft.Text("Stock Inventory", size=18, weight=ft.FontWeight.W_600),
        product_list_column,

        ft.Divider(),

        # SECTION 3: Add New Product Form
        ft.Text("Add New Item", size=18, weight=ft.FontWeight.W_600),
        ft.Container(
            padding=12,
            border_radius=8,
            bgcolor=ft.Colors.SURFACE_CONTAINER_HIGH,
            content=ft.Column(
                controls=[
                    txt_name,
                    ft.Row([txt_cost, txt_price]),
                    txt_stock,
                    ft.ElevatedButton(
                        "+ Add Item to Inventory",
                        icon=ft.Icons.ADD,
                        bgcolor=ft.Colors.TEAL_700,
                        color=ft.Colors.WHITE,
                        on_click=handle_add_new_product,
                    ),
                ],
                spacing=10,
            ),
        ),
    )

    # Initial load
    refresh_product_list()
    refresh_slip_ui()

if __name__ == "__main__":
    ft.app(target=main)

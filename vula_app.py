"""
================================================================================
 Project: VulaTrade Engine (VulaBiz)
 Architecture: Offline-First Mzansi Enterprise Launch & Trade Utility
 Developer: Phiwithemba Lusanda Ngobese
 Hackathon Entry: FNB App of the Year Hackathon 2026
 Categories: Best Breakthrough Developer | Best South African Solution
 Framework: Python / Flet 1.0+ Engine (Adaptive Mobile UI)
 Storage: Local Embedded SQLite3
 Copyright: (c) 2026 Phiwithemba Lusanda Ngobese. All rights reserved.
================================================================================
"""

__author__ = "Phiwithemba Lusanda Ngobese"
__copyright__ = "Copyright 2026, Phiwithemba Lusanda Ngobese"
__credits__ = ["Phiwithemba Lusanda Ngobese"]
__version__ = "1.0.0"
__maintainer__ = "Phiwithemba Lusanda Ngobese"
__status__ = "Production / Hackathon Submission"

import sqlite3
import datetime
import math
import urllib.parse
from typing import List, Dict, Any, Optional
import flet as ft

DB_FILE = "vulatrade_local.db"

class DatabaseManager:
    @staticmethod
    def get_connection():
        return sqlite3.connect(DB_FILE, check_same_thread=False)

    @classmethod
    def init_db(cls):
        with cls.get_connection() as conn:
            cur = conn.cursor()
            
            cur.execute("""
                CREATE TABLE IF NOT EXISTS system_metadata (
                    meta_key TEXT PRIMARY KEY,
                    meta_val TEXT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cur.execute("""
                INSERT OR IGNORE INTO system_metadata (meta_key, meta_val) VALUES 
                ('application_title', 'VulaTrade Engine'),
                ('lead_developer', 'Phiwithemba Lusanda Ngobese'),
                ('submission_target', 'FNB App of the Year Hackathon 2026'),
                ('categories', 'Best Breakthrough Developer / Best South African Solution'),
                ('architecture', 'Zero-Data Offline Local SQLite Persistence'),
                ('copyright_notice', 'Copyright 2026 Phiwithemba Lusanda Ngobese. All Rights Reserved.')
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS inventory (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    category TEXT NOT NULL,
                    cost_price REAL NOT NULL,
                    selling_price REAL NOT NULL,
                    stock_qty INTEGER NOT NULL,
                    min_threshold INTEGER NOT NULL DEFAULT 5,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS ledger (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    transaction_type TEXT NOT NULL,
                    title TEXT NOT NULL,
                    amount REAL NOT NULL,
                    payment_method TEXT NOT NULL,
                    category TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS milestones (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    category TEXT NOT NULL,
                    is_completed INTEGER NOT NULL DEFAULT 0
                )
            """)

            cur.execute("SELECT COUNT(*) FROM milestones")
            if cur.fetchone()[0] == 0:
                default_milestones = [
                    ("Calculate Unit Economics", "Confirm selling price covers stock, transit, and minimum 25% profit margin.", "Finance", 1),
                    ("Supplier Sourcing Established", "Identify 2 backup suppliers in your township or local CBD to prevent stockouts.", "Operations", 0),
                    ("Secure Float & Payment Options", "Prepare cash float for physical change and sign up for QR/speed-point solution.", "Finance", 0),
                    ("Regulatory & Operating Compliance", "Check CIPC registration or local municipal informal trade permits.", "Legal", 0),
                    ("Launch Stock Purchased", "First physical batch acquired and logged in inventory tracker.", "Stock", 0),
                    ("First 10 Customers Identified", "Engage immediate local network or community groups for pilot sales.", "Marketing", 0)
                ]
                cur.executemany(
                    "INSERT INTO milestones (title, description, category, is_completed) VALUES (?, ?, ?, ?)",
                    default_milestones
                )

            cur.execute("SELECT COUNT(*) FROM inventory")
            if cur.fetchone()[0] == 0:
                default_inventory = [
                    ("Coke 330ml Can", "Cold Drinks", 16.00, 24.00, 24, 6),
                    ("Reboost Energy Drink 500ml", "Cold Drinks", 9.50, 15.00, 18, 5),
                    ("Fresh Potato Chips (Large)", "Snacks", 12.00, 20.00, 10, 4),
                    ("Single Box Matches", "Essentials", 0.90, 1.50, 45, 10),
                    ("Leather Travel Wallet", "Merchandise", 95.00, 180.00, 4, 2)
                ]
                cur.executemany(
                    "INSERT INTO inventory (name, category, cost_price, selling_price, stock_qty, min_threshold) VALUES (?, ?, ?, ?, ?, ?)",
                    default_inventory
                )

            conn.commit()

    @classmethod
    def get_inventory(cls) -> List[Dict[str, Any]]:
        with cls.get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute("SELECT * FROM inventory ORDER BY stock_qty ASC, name ASC")
            return [dict(row) for row in cur.fetchall()]

    @classmethod
    def add_product(cls, name: str, category: str, cost: float, price: float, qty: int, threshold: int):
        with cls.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO inventory (name, category, cost_price, selling_price, stock_qty, min_threshold)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (name, category, cost, price, qty, threshold))
            conn.commit()

    @classmethod
    def delete_product(cls, product_id: int):
        with cls.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM inventory WHERE id = ?", (product_id,))
            conn.commit()

    @classmethod
    def adjust_stock(cls, product_id: int, new_qty: int):
        with cls.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("UPDATE inventory SET stock_qty = ? WHERE id = ?", (new_qty, product_id))
            conn.commit()

    @classmethod
    def get_financial_summary(cls) -> Dict[str, float]:
        with cls.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT TOTAL(amount) FROM ledger WHERE transaction_type = 'SALE'")
            total_sales = cur.fetchone()[0] or 0.0

            cur.execute("SELECT TOTAL(amount) FROM ledger WHERE transaction_type = 'EXPENSE'")
            total_expenses = cur.fetchone()[0] or 0.0

            cur.execute("SELECT TOTAL(cost_price * stock_qty) FROM inventory")
            inventory_asset_value = cur.fetchone()[0] or 0.0

            return {
                "total_sales": total_sales,
                "total_expenses": total_expenses,
                "net_profit": total_sales - total_expenses,
                "inventory_value": inventory_asset_value
            }

    @classmethod
    def record_transaction(cls, t_type: str, title: str, amount: float, method: str, category: str, product_id: Optional[int] = None, qty_sold: int = 1):
        with cls.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO ledger (transaction_type, title, amount, payment_method, category)
                VALUES (?, ?, ?, ?, ?)
            """, (t_type, title, amount, method, category))
            
            if t_type == "SALE" and product_id is not None:
                cur.execute("UPDATE inventory SET stock_qty = MAX(0, stock_qty - ?) WHERE id = ?", (qty_sold, product_id))
            conn.commit()

    @classmethod
    def get_milestones(cls) -> List[Dict[str, Any]]:
        with cls.get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute("SELECT * FROM milestones ORDER BY id ASC")
            return [dict(row) for row in cur.fetchall()]

    @classmethod
    def toggle_milestone(cls, m_id: int, completed: bool):
        with cls.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("UPDATE milestones SET is_completed = ? WHERE id = ?", (1 if completed else 0, m_id))
            conn.commit()

class IntelligenceAdvisor:
    @staticmethod
    def audit_business() -> List[Dict[str, str]]:
        insights = []
        summary = DatabaseManager.get_financial_summary()
        inventory = DatabaseManager.get_inventory()

        critical_items = [i for i in inventory if i['stock_qty'] <= i['min_threshold']]
        if critical_items:
            names = ", ".join([i['name'] for i in critical_items[:3]])
            insights.append({
                "type": "WARNING",
                "badge": "RESTOCK REQUIRED",
                "color": "#D32F2F",
                "title": f"{len(critical_items)} Items Below Reserve Threshold",
                "desc": f"Items nearing depletion: {names}. Avoid stockouts to protect local client loyalty."
            })
        else:
            insights.append({
                "type": "SUCCESS",
                "badge": "INVENTORY HEALTHY",
                "color": "#2E7D32",
                "title": "All Tracked Products In Safe Quantities",
                "desc": "Stock reserve levels are currently above minimum operating buffers."
            })

        if summary['total_sales'] == 0 and summary['total_expenses'] > 0:
            insights.append({
                "type": "DANGER",
                "badge": "CASH BURN ALERT",
                "color": "#C62828",
                "title": "Expenses Logged with Zero Revenue",
                "desc": f"You have logged R{summary['total_expenses']:.2f} in outflows without registered sales. Prioritize fast-turnover cash generation."
            })
        elif summary['net_profit'] < 0:
            insights.append({
                "type": "WARNING",
                "badge": "OPERATING DEFICIT",
                "color": "#E65100",
                "title": "Outflows Exceed Inflows",
                "desc": f"Operating at a net loss of R{abs(summary['net_profit']):.2f}. Ensure transport is factored into prices."
            })
        elif summary['net_profit'] > 0:
            margin = (summary['net_profit'] / summary['total_sales']) * 100 if summary['total_sales'] > 0 else 0
            insights.append({
                "type": "SUCCESS",
                "badge": "HEALTHY NET SPREAD",
                "color": "#1565C0",
                "title": f"Net Surplus: R{summary['net_profit']:.2f} ({margin:.1f}% Margin)",
                "desc": "Maintain cash discipline. Reinvest at least 60% of operating surplus into high-turnover lines."
            })

        if summary['inventory_value'] > 0 and summary['total_sales'] < (summary['inventory_value'] * 0.25):
            insights.append({
                "type": "INFO",
                "badge": "WORKING CAPITAL TIP",
                "color": "#6A1B9A",
                "title": f"R{summary['inventory_value']:.2f} Stored in Idle Stock",
                "desc": "Capital is tied to physical shelves. Offer bundles or promote daily fast-sellers to unlock liquidity."
            })

        return insights

def main(page: ft.Page):
    page.title = "VulaTrade Engine"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 0

    DatabaseManager.init_db()
    current_nav_index = 0

    snack = ft.SnackBar(content=ft.Text(""), open=False)
    page.overlay.append(snack)

    def show_alert(message: str, error: bool = False):
        snack.content = ft.Text(message, color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD)
        snack.bgcolor = "#B71C1C" if error else "#1B5E20"
        snack.open = True
        page.update()

    def close_dev_dialog(e=None):
        dev_dialog.open = False
        page.update()

    dev_dialog = ft.AlertDialog(
        modal=True,
        title=ft.Row([
            ft.Icon(ft.Icons.VERIFIED, color="#00E676", size=22),
            ft.Text("Developer Credentials", weight=ft.FontWeight.BOLD, size=15)
        ]),
        content=ft.Container(
            width=360,
            content=ft.Column(
                tight=True,
                spacing=8,
                controls=[
                    ft.Text("APPLICATION PROFILE", size=10, weight=ft.FontWeight.BOLD, color="#90CAF9"),
                    ft.Text("VulaTrade Engine (VulaBiz) v1.0.0", size=13, weight=ft.FontWeight.BOLD),
                    ft.Text("Offline-first micro-enterprise launch and unit economics management system designed for emerging South African founders.", size=11, color="#B0BEC5"),
                    ft.Divider(color="#2C343F"),
                    ft.Text("AUTHORSHIP & INTELLECTUAL PROPERTY", size=10, weight=ft.FontWeight.BOLD, color="#90CAF9"),
                    ft.Row([
                        ft.Text("Lead Architect:", size=11, color="#78909C"),
                        ft.Text("Phiwithemba Lusanda Ngobese", size=11, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE)
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    ft.Row([
                        ft.Text("Hackathon Entry:", size=11, color="#78909C"),
                        ft.Text("FNB App of the Year 2026", size=11, weight=ft.FontWeight.BOLD, color="#00E676")
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    ft.Row([
                        ft.Text("Tracks:", size=11, color="#78909C"),
                        ft.Text("Breakthrough Developer / SA Solution", size=11, color="#ECEFF1")
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    ft.Divider(color="#2C343F"),
                    ft.Text("© 2026 Phiwithemba Lusanda Ngobese. All rights reserved.", size=10, color="#78909C")
                ]
            )
        ),
        actions=[
            ft.Button("Close", on_click=close_dev_dialog)
        ],
        open=False
    )
    page.overlay.append(dev_dialog)

    def open_dev_dialog(e=None):
        dev_dialog.open = True
        page.update()

    # VIEW 1: DASHBOARD (Optimized for Mobile)
    def build_dashboard_view():
        summary = DatabaseManager.get_financial_summary()
        insights = IntelligenceAdvisor.audit_business()
        inventory = DatabaseManager.get_inventory()

        def make_mobile_card(title: str, value: str, color_hex: str, icon_name: str):
            return ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Row(
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            controls=[
                                ft.Text(title, size=11, color="#B0BEC5", weight=ft.FontWeight.W_500),
                                ft.Icon(icon_name, size=16, color=color_hex)
                            ]
                        ),
                        ft.Text(value, size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                    ],
                    spacing=2
                ),
                bgcolor="#1E242B",
                border=ft.Border.all(1, "#2C343F"),
                border_radius=8,
                padding=10,
                expand=True
            )

        grid_row1 = ft.Row(
            spacing=8,
            controls=[
                make_mobile_card("Revenue", f"R{summary['total_sales']:.2f}", "#00C853", ft.Icons.ATTACH_MONEY),
                make_mobile_card("Outflows", f"R{summary['total_expenses']:.2f}", "#FF5252", ft.Icons.MONEY_OFF),
            ]
        )
        grid_row2 = ft.Row(
            spacing=8,
            controls=[
                make_mobile_card("Net Margin", f"R{summary['net_profit']:.2f}", "#00B0FF", ft.Icons.SHOW_CHART),
                make_mobile_card("Inventory", f"R{summary['inventory_value']:.2f}", "#FFD600", ft.Icons.INVENTORY_2),
            ]
        )

        advisory_cards = []
        for item in insights:
            advisory_cards.append(
                ft.Container(
                    content=ft.Column(
                        spacing=4,
                        controls=[
                            ft.Row([
                                ft.Container(
                                    content=ft.Text(item['badge'], size=8, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                                    bgcolor=item['color'],
                                    border_radius=4,
                                    padding=ft.Padding.symmetric(horizontal=6, vertical=2)
                                ),
                                ft.Text(item['title'], size=12, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE, expand=True)
                            ]),
                            ft.Text(item['desc'], size=10, color="#B0BEC5")
                        ]
                    ),
                    bgcolor="#181D23",
                    border=ft.Border(left=ft.BorderSide(3, item['color'])),
                    border_radius=6,
                    padding=10
                )
            )

        fast_sale_options = [ft.dropdown.Option(str(i['id']), f"{i['name']} (R{i['selling_price']:.2f})") for i in inventory if i['stock_qty'] > 0]
        
        prod_dropdown = ft.Dropdown(
            label="Select Product",
            options=fast_sale_options,
            border_color="#37474F",
            height=48
        )
        qty_input = ft.TextField(label="Qty", value="1", width=70, text_align=ft.TextAlign.CENTER, height=48)
        method_dropdown = ft.Dropdown(
            label="Payment Mode",
            value="CASH",
            options=[
                ft.dropdown.Option("CASH", "Cash"),
                ft.dropdown.Option("EFT", "Bank EFT"),
                ft.dropdown.Option("CARD", "Card"),
                ft.dropdown.Option("INFORMAL_CREDIT", "Credit Book")
            ],
            expand=True,
            height=48
        )

        def handle_quick_sale(e):
            if not prod_dropdown.value:
                show_alert("Select an in-stock product", error=True)
                return
            try:
                selected_id = int(prod_dropdown.value)
                qty = int(qty_input.value)
                if qty <= 0:
                    raise ValueError()
            except ValueError:
                show_alert("Invalid quantity", error=True)
                return

            item_match = next((x for x in inventory if x['id'] == selected_id), None)
            if not item_match:
                return

            if item_match['stock_qty'] < qty:
                show_alert(f"Only {item_match['stock_qty']} available!", error=True)
                return

            total_val = item_match['selling_price'] * qty
            DatabaseManager.record_transaction(
                t_type="SALE",
                title=f"Sale: {qty}x {item_match['name']}",
                amount=total_val,
                method=method_dropdown.value,
                category="Retail",
                product_id=selected_id,
                qty_sold=qty
            )
            show_alert(f"Logged sale: R{total_val:.2f}!")
            render_current_view()

        quick_sale_box = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text("QUICK TRADE: RECORD SALE", size=10, weight=ft.FontWeight.BOLD, color="#78909C"),
                    prod_dropdown,
                    ft.Row(controls=[qty_input, method_dropdown], spacing=8),
                    ft.Button(
                        "Log Instant Sale",
                        icon=ft.Icons.POINT_OF_SALE,
                        on_click=handle_quick_sale,
                        style=ft.ButtonStyle(
                            bgcolor="#00C853",
                            color=ft.Colors.BLACK,
                            shape=ft.RoundedRectangleBorder(radius=6)
                        )
                    )
                ],
                spacing=8
            ),
            bgcolor="#1E242B",
            border=ft.Border.all(1, "#2C343F"),
            border_radius=8,
            padding=12
        )

        return ft.Column(
            scroll=ft.ScrollMode.AUTO,
            spacing=12,
            controls=[
                grid_row1,
                grid_row2,
                quick_sale_box,
                ft.Text("Business Heuristics & Advisories", size=12, weight=ft.FontWeight.BOLD, color="#ECEFF1"),
                ft.Column(spacing=6, controls=advisory_cards)
            ]
        )

    # VIEW 2: PRICING SIMULATOR
    def build_pricing_calculator_view():
        cost_input = ft.TextField(label="Wholesale Cost / Unit (R)", value="15.00", keyboard_type=ft.KeyboardType.NUMBER)
        units_batch_input = ft.TextField(label="Batch Units Purchased", value="20", keyboard_type=ft.KeyboardType.NUMBER)
        transit_cost_input = ft.TextField(label="Logistics / Taxi Fare (R)", value="30.00", keyboard_type=ft.KeyboardType.NUMBER)
        shrinkage_input = ft.TextField(label="Waste / Spoilage Buffer (%)", value="5.0", keyboard_type=ft.KeyboardType.NUMBER)
        target_margin_input = ft.TextField(label="Target Profit Margin (%)", value="35.0", keyboard_type=ft.KeyboardType.NUMBER)

        result_true_cost = ft.Text("R 0.00", size=15, weight=ft.FontWeight.BOLD, color="#FFB300")
        result_rec_price = ft.Text("R 0.00", size=22, weight=ft.FontWeight.BOLD, color="#00E676")
        result_net_unit_profit = ft.Text("R 0.00", size=15, weight=ft.FontWeight.BOLD, color="#00B0FF")
        result_breakeven_units = ft.Text("0 Units", size=14, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE)
        recommendation_badge = ft.Text("", size=11, color="#B0BEC5")

        def recalculate(e=None):
            try:
                base_cost = float(cost_input.value or 0)
                batch_units = max(1.0, float(units_batch_input.value or 1))
                transit_cost = float(transit_cost_input.value or 0)
                shrinkage_pct = float(shrinkage_input.value or 0) / 100.0
                target_margin_pct = float(target_margin_input.value or 0) / 100.0

                allocated_transit = transit_cost / batch_units
                subtotal_cost = base_cost + allocated_transit
                true_landing_cost = subtotal_cost * (1.0 + shrinkage_pct)
                
                safe_margin = min(target_margin_pct, 0.85)
                rec_selling_price = true_landing_cost / (1.0 - safe_margin)
                unit_profit = rec_selling_price - true_landing_cost

                total_batch_outlay = (base_cost * batch_units) + transit_cost
                breakeven_units = math.ceil(total_batch_outlay / rec_selling_price) if rec_selling_price > 0 else 0

                result_true_cost.value = f"R {true_landing_cost:.2f}"
                result_rec_price.value = f"R {rec_selling_price:.2f}"
                result_net_unit_profit.value = f"R {unit_profit:.2f}"
                result_breakeven_units.value = f"{breakeven_units} of {int(batch_units)} Units"

                if safe_margin < 0.20:
                    recommendation_badge.value = "⚠️ Margin below 20% leaves little buffer for sudden transit hikes."
                    recommendation_badge.color = "#FF9800"
                else:
                    recommendation_badge.value = "✅ Sound pricing: Protects profit margins while amortizing travel overhead."
                    recommendation_badge.color = "#4CAF50"

                page.update()
            except ValueError:
                pass

        for control in [cost_input, units_batch_input, transit_cost_input, shrinkage_input, target_margin_input]:
            control.on_change = recalculate

        recalculate()

        return ft.Column(
            scroll=ft.ScrollMode.AUTO,
            spacing=12,
            controls=[
                ft.Text("Unit Economics Simulator", size=16, weight=ft.FontWeight.BOLD),
                ft.Container(
                    content=ft.Column(
                        spacing=10,
                        controls=[
                            cost_input,
                            units_batch_input,
                            transit_cost_input,
                            shrinkage_input,
                            target_margin_input,
                        ]
                    ),
                    bgcolor="#1E242B",
                    border=ft.Border.all(1, "#2C343F"),
                    border_radius=8,
                    padding=12
                ),
                ft.Container(
                    content=ft.Column(
                        spacing=10,
                        controls=[
                            ft.Text("RECOMMENDED PRICE", size=10, weight=ft.FontWeight.BOLD, color="#B0BEC5"),
                            result_rec_price,
                            ft.Row([
                                ft.Column([ft.Text("Landed Cost", size=10, color="#B0BEC5"), result_true_cost]),
                                ft.Column([ft.Text("Profit/Unit", size=10, color="#B0BEC5"), result_net_unit_profit]),
                                ft.Column([ft.Text("Break-Even", size=10, color="#B0BEC5"), result_breakeven_units]),
                            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                            recommendation_badge
                        ]
                    ),
                    bgcolor="#181D23",
                    border=ft.Border.all(1, "#2C343F"),
                    border_radius=8,
                    padding=12
                )
            ]
        )

    # VIEW 3: INVENTORY TRACKER (With Item Deletion & Out-of-Stock Protection)
    def build_inventory_view():
        inventory = DatabaseManager.get_inventory()

        name_in = ft.TextField(label="Product Name", hint_text="e.g. Scone / Biscuit")
        cat_in = ft.Dropdown(
            label="Category",
            options=[
                ft.dropdown.Option("Snacks", "Snacks"),
                ft.dropdown.Option("Cold Drinks", "Cold Drinks"),
                ft.dropdown.Option("Essentials", "Essentials"),
                ft.dropdown.Option("Merchandise", "Merchandise"),
                ft.dropdown.Option("Services", "Services / Printing")
            ],
            value="Essentials"
        )
        cost_in = ft.TextField(label="Wholesale Cost (R)", keyboard_type=ft.KeyboardType.NUMBER, expand=True)
        price_in = ft.TextField(label="Retail Price (R)", keyboard_type=ft.KeyboardType.NUMBER, expand=True)
        qty_in = ft.TextField(label="Initial Qty", keyboard_type=ft.KeyboardType.NUMBER, value="10")

        def add_item_click(e):
            if not name_in.value or not cost_in.value or not price_in.value or not qty_in.value:
                show_alert("Complete all product fields (Name, Cost, Price, Qty)", error=True)
                return
            try:
                c = float(cost_in.value)
                p = float(price_in.value)
                q = int(qty_in.value)
                DatabaseManager.add_product(name_in.value, cat_in.value, c, p, q, 5)
                show_alert(f"Added {name_in.value} to stock!")
                name_in.value = ""
                cost_in.value = ""
                price_in.value = ""
                qty_in.value = "10"
                render_current_view()
            except ValueError:
                show_alert("Cost, Price, and Qty must be valid numbers", error=True)

        def prompt_delete_product(prod_id: int, prod_name: str):
            def confirm_delete(ev):
                DatabaseManager.delete_product(prod_id)
                delete_dialog.open = False
                page.update()
                show_alert(f"Deleted '{prod_name}' from inventory.")
                render_current_view()

            def dismiss_delete(ev):
                delete_dialog.open = False
                page.update()

            delete_dialog = ft.AlertDialog(
                modal=True,
                title=ft.Row([
                    ft.Icon(ft.Icons.DELETE_FOREVER, color="#FF5252", size=22),
                    ft.Text("Delete Product", weight=ft.FontWeight.BOLD, size=15)
                ]),
                content=ft.Text(f"Are you sure you want to permanently remove '{prod_name}'?", size=12),
                actions=[
                    ft.TextButton("Cancel", on_click=dismiss_delete),
                    ft.Button(
                        "Delete",
                        on_click=confirm_delete,
                        style=ft.ButtonStyle(bgcolor="#D32F2F", color=ft.Colors.WHITE)
                    )
                ]
            )
            page.overlay.append(delete_dialog)
            delete_dialog.open = True
            page.update()

        inventory_cards = []
        for item in inventory:
            is_out = item['stock_qty'] <= 0
            is_low = (item['stock_qty'] <= item['min_threshold']) and not is_out

            status_badge_color = "#371818" if (is_low or is_out) else "#142D1C"
            status_text_color = "#FF5252" if (is_low or is_out) else "#69F0AE"
            status_label = "OUT OF STOCK" if is_out else f"{item['stock_qty']} left"
            
            def make_adjust_handler(p_id, cur_q, delta):
                return lambda e: (DatabaseManager.adjust_stock(p_id, max(0, cur_q + delta)), render_current_view())

            inventory_cards.append(
                ft.Container(
                    content=ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[
                            ft.Column([
                                ft.Text(
                                    item['name'],
                                    size=13,
                                    weight=ft.FontWeight.BOLD,
                                    color=ft.Colors.GREY_500 if is_out else ft.Colors.WHITE
                                ),
                                ft.Text(f"{item['category']} | Cost: R{item['cost_price']:.2f} | Retail: R{item['selling_price']:.2f}", size=10, color="#78909C")
                            ], expand=True),
                            ft.Row([
                                ft.Container(
                                    content=ft.Text(status_label, size=11, weight=ft.FontWeight.BOLD, color=status_text_color),
                                    bgcolor=status_badge_color,
                                    padding=ft.Padding.symmetric(horizontal=6, vertical=2),
                                    border_radius=4
                                ),
                                ft.IconButton(ft.Icons.REMOVE, icon_size=16, on_click=make_adjust_handler(item['id'], item['stock_qty'], -1)),
                                ft.IconButton(ft.Icons.ADD, icon_size=16, on_click=make_adjust_handler(item['id'], item['stock_qty'], 1)),
                                ft.IconButton(
                                    ft.Icons.DELETE_OUTLINE,
                                    icon_color="#FF5252",
                                    icon_size=18,
                                    tooltip="Delete Item",
                                    on_click=lambda e, pid=item['id'], pname=item['name']: prompt_delete_product(pid, pname)
                                )
                            ], spacing=2)
                        ]
                    ),
                    bgcolor="#181D23",
                    border=ft.Border.all(1, "#263238"),
                    border_radius=6,
                    padding=10
                )
            )

        return ft.Column(
            scroll=ft.ScrollMode.AUTO,
            spacing=12,
            controls=[
                ft.Text("Inventory Management", size=16, weight=ft.FontWeight.BOLD),
                ft.Container(
                    content=ft.Column([
                        name_in,
                        cat_in,
                        ft.Row([cost_in, price_in], spacing=8),
                        qty_in,
                        ft.Button(
                            "Add Stock Item",
                            icon=ft.Icons.ADD_BOX,
                            on_click=add_item_click,
                            style=ft.ButtonStyle(bgcolor="#1E88E5", color=ft.Colors.WHITE)
                        )
                    ], spacing=10),
                    bgcolor="#1E242B",
                    padding=12,
                    border_radius=8
                ),
                ft.Column(spacing=6, controls=inventory_cards)
            ]
        )

    # VIEW 4: DIGITAL RECEIPT GENERATOR (With Paid Amount & Change Calculation)
    def build_receipt_generator_view():
        inventory = DatabaseManager.get_inventory()

        cust_name_in = ft.TextField(label="Client Name", value="Walk-in Client")
        biz_name_in = ft.TextField(label="Trading Entity", value="KwaNgobese Enterprise")
        
        # Only in-stock items can be selected for a receipt
        in_stock_inventory = [i for i in inventory if i['stock_qty'] > 0]
        item_options = [ft.dropdown.Option(str(i['id']), f"{i['name']} (R{i['selling_price']:.2f})") for i in in_stock_inventory]

        item_drop = ft.Dropdown(
            label="Item",
            options=item_options,
            expand=True
        )
        qty_drop = ft.TextField(label="Qty", value="1", width=60)
        cash_paid_in = ft.TextField(label="Cash Tendered (R)", keyboard_type=ft.KeyboardType.NUMBER, hint_text="e.g. 50.00")
        change_display = ft.Text("Change: R 0.00", size=13, weight=ft.FontWeight.BOLD, color="#FFB300")
        
        cart: List[Dict[str, Any]] = []
        receipt_preview = ft.TextField(
            label="Digital WhatsApp Invoice",
            multiline=True,
            read_only=True,
            min_lines=10,
            max_lines=14,
            text_size=11
        )

        def get_cart_total() -> float:
            return sum(c['price'] * c['qty'] for c in cart)

        def generate_receipt_text(e=None):
            now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
            total = get_cart_total()

            paid_val = total
            change_val = 0.0
            paid_str = cash_paid_in.value.strip() if cash_paid_in.value else ""
            
            if paid_str:
                try:
                    paid_val = float(paid_str)
                    if paid_val < total:
                        short = total - paid_val
                        change_display.value = f"Short: R {short:.2f}"
                        change_display.color = "#FF5252"
                    else:
                        change_val = paid_val - total
                        change_display.value = f"Change Due: R {change_val:.2f}"
                        change_display.color = "#00E676"
                except ValueError:
                    change_display.value = "Invalid cash entered"
                    change_display.color = "#FF5252"
            else:
                change_display.value = "Change: R 0.00"
                change_display.color = "#FFB300"

            lines = [
                "================================",
                f"   {biz_name_in.value.upper()}   ",
                "   OFFLINE DIGITAL RECEIPT SLIP   ",
                "================================",
                f"Date: {now_str}",
                f"Client: {cust_name_in.value}",
                "--------------------------------",
                "ITEMS:"
            ]
            for idx, c in enumerate(cart, 1):
                item_tot = c['price'] * c['qty']
                lines.append(f"{idx}. {c['name']} x{c['qty']} @ R{c['price']:.2f} = R{item_tot:.2f}")

            lines.extend([
                "--------------------------------",
                f"TOTAL DUE: R {total:.2f}",
                f"CASH PAID: R {paid_val:.2f}",
                f"CHANGE: R {change_val:.2f}",
                "STATUS: SETTLED IN FULL",
                "================================",
                "Thank you for supporting local business!",
                "Powered by VulaTrade Engine"
            ])
            receipt_preview.value = "\n".join(lines)
            page.update()

        cash_paid_in.on_change = generate_receipt_text

        def add_to_cart_click(e):
            if not item_drop.value:
                show_alert("Select an in-stock product", error=True)
                return
            p_id = int(item_drop.value)
            matched = next((x for x in inventory if x['id'] == p_id), None)
            if not matched:
                return

            if matched['stock_qty'] <= 0:
                show_alert(f"'{matched['name']}' is out of stock!", error=True)
                return

            try:
                qty = int(qty_drop.value or 1)
                if qty <= 0:
                    raise ValueError()
            except ValueError:
                show_alert("Invalid quantity", error=True)
                return

            # Prevent cart from exceeding available inventory
            current_in_cart = sum(c['qty'] for c in cart if c['id'] == p_id)
            if (current_in_cart + qty) > matched['stock_qty']:
                show_alert(f"Only {matched['stock_qty']} available in stock!", error=True)
                return

            cart.append({
                "id": p_id,
                "name": matched['name'],
                "price": matched['selling_price'],
                "qty": qty
            })
            show_alert(f"Added {matched['name']} (x{qty})")
            generate_receipt_text()

        def copy_to_clipboard_click(e):
            if not cart:
                show_alert("Receipt empty: add items first", error=True)
                return

            total = get_cart_total()
            paid_str = cash_paid_in.value.strip() if cash_paid_in.value else ""
            if paid_str:
                try:
                    if float(paid_str) < total:
                        show_alert("Cash paid is less than total amount due!", error=True)
                        return
                except ValueError:
                    show_alert("Enter a valid numerical cash amount", error=True)
                    return

            # Deduct sold items from inventory database
            for c in cart:
                DatabaseManager.record_transaction(
                    t_type="SALE",
                    title=f"Receipt Sale: {c['qty']}x {c['name']}",
                    amount=c['price'] * c['qty'],
                    method="CASH",
                    category="Retail Slip",
                    product_id=c['id'],
                    qty_sold=c['qty']
                )

            # Copy receipt to clipboard
            page.clipboard = receipt_preview.value
            show_alert("Slip copied to clipboard! Opening WhatsApp...")

            # Open WhatsApp with encoded receipt text
            encoded = urllib.parse.quote(receipt_preview.value)
            page.launch_url(f"https://wa.me/?text={encoded}")

            # Reset cart and refresh view
            cart.clear()
            cash_paid_in.value = ""
            render_current_view()

        generate_receipt_text()

        return ft.Column(
            scroll=ft.ScrollMode.AUTO,
            spacing=12,
            controls=[
                ft.Text("Digital Slip Generator", size=16, weight=ft.FontWeight.BOLD),
                ft.Container(
                    content=ft.Column([
                        biz_name_in,
                        cust_name_in,
                        ft.Row([item_drop, qty_drop], spacing=6),
                        ft.Button(
                            "Add Item to Invoice",
                            icon=ft.Icons.POST_ADD,
                            on_click=add_to_cart_click,
                            style=ft.ButtonStyle(bgcolor="#0288D1", color=ft.Colors.WHITE)
                        ),
                        ft.Divider(color="#263238"),
                        cash_paid_in,
                        change_display
                    ], spacing=8),
                    bgcolor="#1E242B",
                    padding=12,
                    border_radius=8
                ),
                receipt_preview,
                ft.Button(
                    "Finalize & Share via WhatsApp",
                    icon=ft.Icons.SHARE,
                    on_click=copy_to_clipboard_click,
                    style=ft.ButtonStyle(bgcolor="#00C853", color=ft.Colors.BLACK)
                )
            ]
        )

    # VIEW 5: MILESTONES
    def build_milestones_view():
        milestones = DatabaseManager.get_milestones()
        total_m = len(milestones)
        completed_m = sum(1 for m in milestones if m['is_completed'] == 1)
        progress_val = completed_m / total_m if total_m > 0 else 0.0

        def toggle_click(m_id, current_state):
            def handler(e):
                DatabaseManager.toggle_milestone(m_id, not current_state)
                render_current_view()
            return handler

        milestone_widgets = []
        for m in milestones:
            done = (m['is_completed'] == 1)
            milestone_widgets.append(
                ft.Container(
                    content=ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[
                            ft.Row([
                                ft.Checkbox(value=done, on_change=toggle_click(m['id'], done)),
                                ft.Column([
                                    ft.Text(m['title'], size=12, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE if not done else "#9E9E9E"),
                                    ft.Text(m['description'], size=10, color="#78909C")
                                ], spacing=1, expand=True)
                            ], expand=True),
                        ]
                    ),
                    bgcolor="#181D23",
                    border=ft.Border.all(1, "#263238"),
                    border_radius=6,
                    padding=8
                )
            )

        return ft.Column(
            scroll=ft.ScrollMode.AUTO,
            spacing=12,
            controls=[
                ft.Text("Launch Readiness Checklist", size=16, weight=ft.FontWeight.BOLD),
                ft.Container(
                    content=ft.Column([
                        ft.Row(
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            controls=[
                                ft.Text("Readiness Progress", size=12, weight=ft.FontWeight.BOLD),
                                ft.Text(f"{int(progress_val * 100)}%", size=12, weight=ft.FontWeight.BOLD, color="#00E676")
                            ]
                        ),
                        ft.ProgressBar(value=progress_val, color="#00E676", bgcolor="#263238")
                    ], spacing=4),
                    bgcolor="#1E242B",
                    padding=10,
                    border_radius=8
                ),
                ft.Column(spacing=6, controls=milestone_widgets)
            ]
        )

    # ROOT CONTAINER & VIEW RENDERER
    workspace = ft.Container(expand=True, padding=12, bgcolor="#12161A")

    def render_current_view():
        if current_nav_index == 0:
            workspace.content = build_dashboard_view()
        elif current_nav_index == 1:
            workspace.content = build_pricing_calculator_view()
        elif current_nav_index == 2:
            workspace.content = build_inventory_view()
        elif current_nav_index == 3:
            workspace.content = build_receipt_generator_view()
        elif current_nav_index == 4:
            workspace.content = build_milestones_view()
        page.update()

    def handle_nav_change(e):
        nonlocal current_nav_index
        current_nav_index = e.control.selected_index
        render_current_view()

    # Mobile App Bar with Direct Developer Credentials Access
    page.appbar = ft.AppBar(
        leading=ft.Icon(ft.Icons.SAVINGS, color="#00E676", size=24),
        title=ft.Column([
            ft.Text("VulaTrade Engine", size=14, weight=ft.FontWeight.BOLD),
            ft.Text("Offline Mzansi Utility • 100% Local Data", size=9, color="#00E676")
        ], spacing=1),
        bgcolor="#181D23",
        actions=[
            ft.IconButton(
                icon=ft.Icons.BADGE_OUTLINED,
                icon_color="#90CAF9",
                tooltip="Developer Profile",
                on_click=open_dev_dialog
            )
        ]
    )

    # Bottom Navigation Bar
    page.navigation_bar = ft.NavigationBar(
        selected_index=0,
        bgcolor="#181D23",
        destinations=[
            ft.NavigationBarDestination(icon=ft.Icons.DASHBOARD_OUTLINED, selected_icon=ft.Icons.DASHBOARD, label="Dash"),
            ft.NavigationBarDestination(icon=ft.Icons.CALCULATE_OUTLINED, selected_icon=ft.Icons.CALCULATE, label="Pricing"),
            ft.NavigationBarDestination(icon=ft.Icons.INVENTORY_2_OUTLINED, selected_icon=ft.Icons.INVENTORY_2, label="Stock"),
            ft.NavigationBarDestination(icon=ft.Icons.RECEIPT_LONG_OUTLINED, selected_icon=ft.Icons.RECEIPT_LONG, label="Slips"),
            ft.NavigationBarDestination(icon=ft.Icons.CHECKLIST_OUTLINED, selected_icon=ft.Icons.CHECKLIST, label="Checklist"),
        ],
        on_change=handle_nav_change
    )

    page.add(workspace)
    render_current_view()

# Resilient dual entrypoint: compatible with desktop and Android serious_python runtime
if __name__ == "__main__":
    if hasattr(ft, "run"):
        ft.run(main)
    else:
        ft.app(target=main)
from tkinter import ttk
import customtkinter
from tkcalendar import Calendar, DateEntry
from datetime import *
from ZODB import DB
from ZODB.FileStorage import FileStorage
import transaction
import uuid
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.ticker import FuncFormatter
from matplotlib.figure import Figure

class MoneyManagerApp(customtkinter.CTk):
    def __init__(self):
        super().__init__()
        self.title("Money Manager")
        self.geometry("800x600")
        global categories 
        categories = ["Food", "Transport", "Rent", "Salary", "Freelance", "Bonous","Others"]
        customtkinter.set_appearance_mode("dark")

        # ZODB Setup
        self.setup_db()

        self.menu = Menu(master=self, callback=self.filter_data_by_month, get_data_callback=self.get_data)
        self.menu.pack()


    def setup_db(self):
        self.storage = FileStorage("money_manager.fs")
        self.db = DB(self.storage)
        self.connection = self.db.open()
        self.root = self.connection.root()
        self.root.clear()  # Clear the root object

    def load_data(self):
        income_data = self.root.get("income", {})
        expense_data = self.root.get("expense", {})

        all_data = {}
        all_dates = set(income_data.keys()) | set(expense_data.keys())

        for date in all_dates:
            combined_entries = []
            if date in income_data:
                combined_entries.extend(income_data[date])
            if date in expense_data:
                combined_entries.extend(expense_data[date])
            all_data[date] = combined_entries

        # Update both dashboard and accounts based on all data
        self.update_dashboard_totals(all_data)
        self.menu.dashboard.show_data(all_data)


    def add_expense(self):
        self.add_expense = AddExpense(master=self, callback=self.save_expense)

    def save_expense(self, data):

        date, entry = list(data.items())[0]
        type_u = entry[0]["type"]

        if type_u == "Income":
            if "income" not in self.root:
                self.root["income"] = {}  
            if date not in self.root["income"]:
                self.root["income"][date] = []  
            self.root["income"][date].append(entry[0])  
        else:
            if "expense" not in self.root:
                self.root["expense"] = {}  
            if date not in self.root["expense"]:
                self.root["expense"][date] = [] 
            self.root["expense"][date].append(entry[0])

        transaction.commit()
        self.load_data()

        # Update comboboxes and filter data
        self.update_combobox_to_date(date)
        current_month = self.menu.dashboard_label.month_combobox.get()
        current_year = self.menu.dashboard_label.year_combobox.get()
        self.filter_data_by_month(f"{current_month} {current_year}")

    def update_combobox_to_date(self, date):
        entry_date = datetime.strptime(date, "%d/%m/%Y")
        month_name = entry_date.strftime("%B")
        year = str(entry_date.year)

        self.menu.dashboard_label.set_month_year(month_name, year)
        

    def edit_entry(self, unique_id):
        for date, entries in self.root.get("income", {}).items():
            for entry in entries:
                if entry["unique_id"] == unique_id:
                    self.open_edit_form(date, entry, "income")

        for date, entries in self.root.get("expense", {}).items():
            for entry in entries:
                if entry["unique_id"] == unique_id:
                    self.open_edit_form(date, entry, "expense")

    def delete_entry(self, unique_id):
        found = False

        # Check and delete from income
        for date, entries in list(self.root.get("income", {}).items()):
            for entry in entries:
                if entry["unique_id"] == unique_id:
                    entries.remove(entry)
                    found = True
                    break
            if not entries:
                del self.root["income"][date]  # Remove the date key if no entries left
            if found:
                break
       
        if not found:  
            for date, entries in list(self.root.get("expense", {}).items()):
                for entry in entries:
                    if entry["unique_id"] == unique_id:
                        entries.remove(entry)
                        found = True
                        break
                if not entries:
                    del self.root["expense"][date] 
                if found:
                    break

        transaction.commit()
        self.load_data()
        self.menu.charts.update_charts()

        current_month = self.menu.dashboard_label.month_combobox.get()
        current_year = self.menu.dashboard_label.year_combobox.get()
        self.filter_data_by_month(f"{current_month} {current_year}")

    def open_edit_form(self, date, entry, entry_type):
        def save_changes(updated_data):
            # Remove the old entry
            if entry_type == "income":
                entries = self.root["income"][date]
            else:
                entries = self.root["expense"][date]

            entries = [e for e in entries if e["unique_id"] != entry["unique_id"]]
            
            if not entries:
                if entry_type == "income":
                    del self.root["income"][date]
                else:
                    del self.root["expense"][date]
            else:
                if entry_type == "income":
                    self.root["income"][date] = entries
                else:
                    self.root["expense"][date] = entries

            new_date = updated_data.get("date", date)
            if updated_data["type"] == "Income":
                if new_date not in self.root["income"]:
                    self.root["income"][new_date] = []
                self.root["income"][new_date].append(updated_data)
            else:
                if new_date not in self.root["expense"]:
                    self.root["expense"][new_date] = []
                self.root["expense"][new_date].append(updated_data)

            transaction.commit()

            current_month = self.menu.dashboard_label.month_combobox.get()
            current_year = self.menu.dashboard_label.year_combobox.get()
            self.filter_data_by_month(f"{current_month} {current_year}")

        EditForm(
            master=self,
            date=date,
            entry=entry,
            callback=save_changes
        )

    def filter_data_by_month(self, selected_month_year):
        income_data = self.root.get("income", {})
        expense_data = self.root.get("expense", {})

        selected_date = datetime.strptime(selected_month_year, "%B %Y")
        selected_month = selected_date.month
        selected_year = selected_date.year

        filtered_data = {}

        for date_str in set(income_data.keys()).union(expense_data.keys()):
            date_obj = datetime.strptime(date_str, "%d/%m/%Y")
            if date_obj.month == selected_month and date_obj.year == selected_year:
                entries = []
                if date_str in income_data:
                    entries.extend(income_data[date_str])
                if date_str in expense_data:
                    entries.extend(expense_data[date_str])
                
                filtered_data[date_str] = entries

        self.menu.dashboard.show_data(filtered_data)
        self.update_dashboard_totals(filtered_data) 
        self.menu.charts.update_charts(filtered_data)

    def update_dashboard_totals(self, filtered_data):
        account_totals = {
            "Cash": {"income": 0, "expense": 0},
            "Bank Account": {"income": 0, "expense": 0},
            "Card": {"income": 0, "expense": 0}
        }

        total_income = 0
        total_expense = 0

        for entries in filtered_data.values():
            for entry in entries:
                amount = float(entry["amount"])
                account_type = entry["account_type"]
                if entry["type"] == "Income":
                    total_income += amount
                    account_totals[account_type]["income"] += amount
                else:
                    total_expense += amount
                    account_totals[account_type]["expense"] += amount

        total_balance = total_income - total_expense

        self.menu.dashboard_label.update(total_income, total_expense, total_balance)
        self.menu.accounts.update_totals(account_totals)

    def get_data(self):
        income_data = dict(self.root.get("income", {}))
        expense_data = dict(self.root.get("expense", {}))

        return {
            "income": income_data,
            "expense": expense_data
        }

class Menu(customtkinter.CTkTabview):
    def __init__(self, master, callback, get_data_callback):
        super().__init__(master)
        self.app = master
        self.add("Dashboard")
        self.add("Charts")
        self.add("Accounts")

        # Dashboard
        self.dashboard_label = Dashboard_Label(master=self.tab("Dashboard"), callback=callback)
        self.dashboard_label.pack()

        self.add_btn = customtkinter.CTkButton(master=self.tab("Dashboard"), text="Add", command=master.add_expense)
        self.add_btn.pack(pady=10)

        self.dashboard = Dashboard(master=self.tab("Dashboard"), app=self.app)
        self.dashboard.pack()

        # Charts
        self.charts = Charts(master=self.tab("Charts"), get_data_callback=get_data_callback)
        self.charts.pack(expand=True, fill="both")

        # Accounts
        self.accounts = Accounts(master=self.tab("Accounts"))
        self.accounts.pack(expand=True, fill="both")

class Dashboard_Label(customtkinter.CTkFrame):
    def __init__(self, master, callback):
        super().__init__(master)
        self.callback = callback

        # Month Selector
        self.month_combobox = ttk.Combobox(self, values=[
            "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December"
        ])
        self.month_combobox.set(datetime.now().strftime("%B"))
        self.month_combobox.bind("<<ComboboxSelected>>", self.update_date)

        # Year Selector
        self.year_combobox = ttk.Combobox(self, values=[str(year) for year in range(2020, 2031)])
        self.year_combobox.set(str(datetime.now().year))
        self.year_combobox.bind("<<ComboboxSelected>>", self.update_date)

        self.month_combobox.grid(row=0, column=0, padx=5, pady=10)
        self.year_combobox.grid(row=0, column=1, padx=5, pady=10)

        self.incomeLabel = customtkinter.CTkLabel(master=self, text="Income")
        self.expenseLabel = customtkinter.CTkLabel(master=self, text="Exp")
        self.totalLabel = customtkinter.CTkLabel(master=self, text="Balance")

        self.income = customtkinter.CTkLabel(master=self, text="0.00")
        self.expense = customtkinter.CTkLabel(master=self, text="0.00")
        self.total = customtkinter.CTkLabel(master=self, text="0.00")


        self.incomeLabel.grid(row=2, column=0, pady=(20,0))
        self.expenseLabel.grid(row=2, column=1, pady=(20,0))
        self.totalLabel.grid(row=2, column=2, pady=(20,0))

        self.income.grid(row=3, column=0, pady=(0,20))
        self.expense.grid(row=3, column=1, pady=(0,20))
        self.total.grid(row=3, column=2, pady=(0,20))
    
    def on_month_change(self, event):
        selected_date = self.month_selector.get_date()
        selected_month_year = selected_date.strftime("%b %Y")
        self.callback(selected_month_year)

    def update(self, total_income, total_expense, total_balance):
        self.income.configure(text=f"${total_income:.2f}")
        self.expense.configure(text=f"${total_expense:.2f}")
        self.total.configure(text=f"${total_balance:.2f}")

    def update_date(self, event=None):
        selected_month = self.month_combobox.get()
        selected_year = self.year_combobox.get()
        selected_month_year = f"{selected_month} {selected_year}"
        self.callback(selected_month_year)
    
    def set_month_year(self, month, year):
        self.month_combobox.set(month)
        self.year_combobox.set(year)
        self.update_date()


class Dashboard(customtkinter.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master)
        self.app = app

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.scrollable_frame = customtkinter.CTkScrollableFrame(master=self, width=780, height=400)
        self.scrollable_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

        self.scrollable_frame.grid_columnconfigure(0, weight=1)
        self.scrollable_frame.grid_columnconfigure(1, weight=1)
        self.scrollable_frame.grid_columnconfigure(2, weight=1)

    def show_data(self,data):
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()

        row = 0  

        for date, entries in data.items():
            
            date_label = customtkinter.CTkLabel(master=self.scrollable_frame, text=date, text_color="lightblue")
            date_label.grid(row=row, column=0, pady=(20, 0), sticky="w")

            
            total_income_amount = sum(float(entry["amount"]) for entry in entries if entry["type"] == "Income")
            total_expense_amount = sum(float(entry["amount"]) for entry in entries if entry["type"] == "Expense")

            total_income = customtkinter.CTkLabel(master=self.scrollable_frame, text=f"$ {total_income_amount:.2f}", text_color="lightblue")
            total_expense = customtkinter.CTkLabel(master=self.scrollable_frame, text=f"$ {total_expense_amount:.2f}", text_color="red")

            total_income.grid(row=row, column=1, pady=(20, 0), sticky="e")
            total_expense.grid(row=row, column=2, pady=(20, 0), sticky="w")

            
            row += 1

            for entry in entries:
                
                exp_type = customtkinter.CTkLabel(master=self.scrollable_frame, text=entry["type"])
                exp_category = customtkinter.CTkLabel(master=self.scrollable_frame, text=entry["category"])
                exp_account = customtkinter.CTkLabel(master=self.scrollable_frame, text=entry["account_type"])
                exp_amt = customtkinter.CTkLabel(master=self.scrollable_frame, text=f"$ {entry['amount']}")

                edit_btn = customtkinter.CTkButton(master=self.scrollable_frame, text="Edit", command=lambda uid=entry["unique_id"]: self.app.edit_entry(uid))
                delete_btn = customtkinter.CTkButton(master=self.scrollable_frame, text="Delete", command=lambda uid=entry["unique_id"]: self.app.delete_entry(uid))

                exp_type.grid(row=row, column=0, pady=(0, 10), sticky="w")
                exp_category.grid(row=row, column=1, pady=(0, 10), sticky="w")
                exp_account.grid(row=row, column=2, pady=(0, 10), sticky="w")
                exp_amt.grid(row=row, column=3, pady=(0, 10), sticky="e")
                edit_btn.grid(row=row, column=4, padx=10, pady=(0, 20), sticky="ns")
                delete_btn.grid(row=row, column=5, padx=10, pady=(0, 20), sticky="ns")

                row += 1  

class Charts(customtkinter.CTkFrame):
    def __init__(self, master, get_data_callback):
        super().__init__(master)
        self.get_data_callback = get_data_callback  # Store the method for fetching data
        self.chart_frame = customtkinter.CTkScrollableFrame(self, width=780, height=600)
        self.chart_frame.pack(fill="both", expand=True)

        self.update_charts(self.get_data_callback())

    def update_charts(self, filtered_data):

        # Clear old charts
        for widget in self.chart_frame.winfo_children():
            widget.destroy()

        self.display_income_vs_expense(filtered_data)
        self.display_income_by_category(filtered_data)
        self.display_expense_by_category(filtered_data)

    def display_income_vs_expense(self, data):
        income_total = sum(
            float(entry["amount"])
            for entries in data.values()
            for entry in entries if entry["type"] == "Income"
        )
        expense_total = sum(
            float(entry["amount"])
            for entries in data.values()
            for entry in entries if entry["type"] == "Expense"
        )

        # Create chart
        fig = Figure(figsize=(5, 3))
        ax = fig.add_subplot(111)
        ax.bar(["Income", "Expense"], [income_total, expense_total], color=["green", "red"])
        ax.set_title("Income vs Expense")

        canvas = FigureCanvasTkAgg(fig, master=self.chart_frame)
        canvas.get_tk_widget().pack()
        canvas.draw()

    def display_income_by_category(self, data):
        category_totals = {}
        
        # Iterate over all entries in the filtered data
        for entries in data.values():
            for entry in entries:
                if entry["type"] == "Income":  # Only consider income entries
                    category = entry["category"]
                    amount = float(entry["amount"])
                    category_totals[category] = category_totals.get(category, 0) + amount

        if category_totals:  # Only plot if there's data
            fig = Figure(figsize=(4, 3))
            ax = fig.add_subplot(111)
            ax.pie(
                category_totals.values(), 
                labels=category_totals.keys(), 
                autopct='%1.1f%%', 
                startangle=140
            )
            ax.set_title("Income by Category")

            canvas = FigureCanvasTkAgg(fig, master=self.chart_frame)
            canvas.get_tk_widget().pack(pady=10)
            canvas.draw()
        else:
            no_data_label = customtkinter.CTkLabel(self.chart_frame, text="No Income Data Available")
            no_data_label.pack(pady=10)

    def display_expense_by_category(self, data):
        category_totals = {}

        # Iterate over all entries in the filtered data
        for entries in data.values():
            for entry in entries:
                if entry["type"] == "Expense":  # Only consider expense entries
                    category = entry["category"]
                    amount = float(entry["amount"])
                    category_totals[category] = category_totals.get(category, 0) + amount

        if category_totals:  # Only plot if there's data
            fig = Figure(figsize=(4, 3))
            ax = fig.add_subplot(111)
            ax.pie(
                category_totals.values(), 
                labels=category_totals.keys(), 
                autopct='%1.1f%%', 
                startangle=140
            )
            ax.set_title("Expense by Category")

            canvas = FigureCanvasTkAgg(fig, master=self.chart_frame)
            canvas.get_tk_widget().pack(pady=10)
            canvas.draw()
        else:
            no_data_label = customtkinter.CTkLabel(self.chart_frame, text="No Expense Data Available")
            no_data_label.pack(pady=10)
        
class Accounts(customtkinter.CTkFrame):
    def __init__(self, master):
        super().__init__(master, width=800, height=300)
        self.pack_propagate(False)
        self.grid_propagate(False)

        self.type = customtkinter.CTkLabel(master=self, text="Type")
        self.income = customtkinter.CTkLabel(master=self, text="Income", text_color="lightblue")
        self.expense = customtkinter.CTkLabel(master=self, text="Expense", text_color="red")
        self.balance = customtkinter.CTkLabel(master=self, text="Balance", text_color="green")

        self.cash_label = customtkinter.CTkLabel(master=self, text="Cash")
        self.cash_income_amount = customtkinter.CTkLabel(master=self, text="$ 0.0", text_color="lightblue")
        self.cash_expense_amount = customtkinter.CTkLabel(master=self, text="$ 0.0", text_color="red")
        self.cash_balance_amount = customtkinter.CTkLabel(master=self, text="$ 0.0", text_color="green")

        self.bank_label = customtkinter.CTkLabel(master=self, text="Bank Account")
        self.bank_income_amount = customtkinter.CTkLabel(master=self, text="$ 0.0", text_color="lightblue")
        self.bank_expense_amount = customtkinter.CTkLabel(master=self, text="$ 0.0", text_color="red")
        self.bank_balance_amount = customtkinter.CTkLabel(master=self, text="$ 0.0", text_color="green")

        self.card_label = customtkinter.CTkLabel(master=self, text="Card")
        self.card_income_amount = customtkinter.CTkLabel(master=self, text="$ 0.0", text_color="lightblue")
        self.card_expense_amount = customtkinter.CTkLabel(master=self, text="$ 0.0", text_color="red")
        self.card_balance_amount = customtkinter.CTkLabel(master=self, text="$ 0.0", text_color="green")

        self.total_label = customtkinter.CTkLabel(master=self, text="Total")
        self.total_income_amount = customtkinter.CTkLabel(master=self, text="$ 0.0", text_color="lightblue")
        self.total_expense_amount = customtkinter.CTkLabel(master=self, text="$ 0.0", text_color="red")
        self.total_balance_amount = customtkinter.CTkLabel(master=self, text="$ 0.0", text_color="green")

        self.grid_columnconfigure(0, weight=1)  
        self.grid_columnconfigure(1, weight=1)  
        self.grid_columnconfigure(2, weight=1)  
        self.grid_columnconfigure(3, weight=1)  

 
        self.type.grid(row=0, column=0, padx=10, pady=(10, 0), sticky="w")
        self.income.grid(row=0, column=1, padx=10, pady=(10, 0))
        self.expense.grid(row=0, column=2, padx=10, pady=(10, 0))
        self.balance.grid(row=0, column=3, padx=10, pady=(10, 0))

        self.cash_label.grid(row=1, column=0, padx=10, pady=10, sticky="w")
        self.cash_income_amount.grid(row=1, column=1, padx=10, pady=10)
        self.cash_expense_amount.grid(row=1, column=2, padx=10, pady=10)
        self.cash_balance_amount.grid(row=1, column=3, padx=10, pady=10)

        self.bank_label.grid(row=2, column=0, padx=10, pady=10, sticky="w")
        self.bank_income_amount.grid(row=2, column=1, padx=10, pady=10)
        self.bank_expense_amount.grid(row=2, column=2, padx=10, pady=10)
        self.bank_balance_amount.grid(row=2, column=3, padx=10, pady=10)

        self.card_label.grid(row=3, column=0, padx=10, pady=10, sticky="w")
        self.card_income_amount.grid(row=3, column=1, padx=10, pady=10)
        self.card_expense_amount.grid(row=3, column=2, padx=10, pady=10)
        self.card_balance_amount.grid(row=3, column=3, padx=10, pady=10)

        self.total_label.grid(row=4, column=0, padx=10, pady=10, sticky="w")
        self.total_income_amount.grid(row=4, column=1, padx=10, pady=10)
        self.total_expense_amount.grid(row=4, column=2, padx=10, pady=10)
        self.total_balance_amount.grid(row=4, column=3, padx=10, pady=10)

    def update_totals(self, account_totals):
        self.cash_income_amount.configure(text=f"$ {account_totals['Cash']['income']:.2f}")
        self.cash_expense_amount.configure(text=f"$ {account_totals['Cash']['expense']:.2f}")
        self.cash_balance_amount.configure(text=f"$ {account_totals['Cash']['income'] - account_totals['Cash']['expense']:.2f}")

        self.bank_income_amount.configure(text=f"$ {account_totals['Bank Account']['income']:.2f}")
        self.bank_expense_amount.configure(text=f"$ {account_totals['Bank Account']['expense']:.2f}")
        self.bank_balance_amount.configure(text=f"$ {account_totals['Bank Account']['income'] - account_totals['Bank Account']['expense']:.2f}")

        self.card_income_amount.configure(text=f"$ {account_totals['Card']['income']:.2f}")
        self.card_expense_amount.configure(text=f"$ {account_totals['Card']['expense']:.2f}")
        self.card_balance_amount.configure(text=f"$ {account_totals['Card']['income'] - account_totals['Card']['expense']:.2f}")

        total_income = sum(account_totals[acc]["income"] for acc in account_totals)
        total_expense = sum(account_totals[acc]["expense"] for acc in account_totals)
        total_balance = sum(account_totals[acc]["income"] - account_totals[acc]["expense"] for acc in account_totals)

        self.total_income_amount.configure(text=f"$ {total_income:.2f}")
        self.total_expense_amount.configure(text=f"$ {total_expense:.2f}")
        self.total_balance_amount.configure(text=f"$ {total_balance:.2f}")

class AddExpense(customtkinter.CTkToplevel):
    def __init__(self, master, callback):
        super().__init__(master)
        self.callback = callback
        self.title("Add Expense")
        self.geometry("350x450")

        # Income / Expense
        self.type_label = customtkinter.CTkLabel(master=self, text="Type")
        self.type_select = customtkinter.CTkComboBox(master=self, values=["Income", "Expense"])
        self.type_label.grid(row=0, column=0, padx=10, pady=10)
        self.type_select.grid(row=0, column=1, padx=10, pady=10, sticky="e")

        # Date Entry
        self.date_label = customtkinter.CTkLabel(master=self, text="Date")
        self.date_entry = Calendar(master=self, selectmode="day", date_pattern="dd/MM/yyyy")
        self.date_label.grid(row=1, column=0, padx=10, pady=10)
        self.date_entry.grid(row=1, column=1, padx=10, pady=10)

        # Amount Entry
        self.amount_label = customtkinter.CTkLabel(master=self, text="Amount")
        self.amount_entry = customtkinter.CTkEntry(master=self, placeholder_text="Enter Amount")
        self.amount_label.grid(row=2, column=0, padx=10, pady=10)
        self.amount_entry.grid(row=2, column=1, padx=10, pady=10, sticky="e")

        # Category Entry
        self.category_label = customtkinter.CTkLabel(master=self, text="Category")
        self.category_select = customtkinter.CTkComboBox(master=self, values=categories)
        self.category_label.grid(row=3, column=0, padx=10, pady=10)
        self.category_select.grid(row=3, column=1, padx=10, pady=10, sticky="e")

        # Account Type
        self.account_label = customtkinter.CTkLabel(master=self, text="Account")
        self.account_select = customtkinter.CTkComboBox(master=self, values=["Cash", "Bank Account", "Card"])
        self.account_label.grid(row=4, column=0, padx=10, pady=10)
        self.account_select.grid(row=4, column=1, padx=10, pady=10, sticky="e")

        # Submit Button
        self.submit_btn = customtkinter.CTkButton(master=self, text="Submit", command=self.submit)
        self.submit_btn.grid(row=5, column=0, columnspan=2, padx=10, pady=10)

    def submit(self):
        date = self.date_entry.get_date()
        amount = self.amount_entry.get()
        type_u = self.type_select.get()
        category = self.category_select.get()
        account = self.account_select.get()
        unique_id = str(uuid.uuid4())

        data = {
            date :[
                {
                    "unique_id": unique_id,
                    "amount": amount, 
                    "type": type_u, 
                    "category": category,
                    "account_type": account
                }
            ]
        }
        self.callback(data)
        self.destroy()
        
class EditForm(customtkinter.CTkToplevel):
    def __init__(self, master, date, entry, callback):
        super().__init__(master)
        self.callback = callback
        self.entry = entry
        self.title("Edit Expense")
        self.geometry("350x450")

        # Date Label
        self.date_label = customtkinter.CTkLabel(master=self, text=f"Date: {date}")
        self.date_label.grid(row=0, column=0, padx=10, pady=10, columnspan=2)

        # Amount
        self.amount_label = customtkinter.CTkLabel(master=self, text="Amount")
        self.amount_entry = customtkinter.CTkEntry(master=self, placeholder_text="Enter Amount")
        self.amount_entry.insert(0, entry["amount"])
        self.amount_label.grid(row=1, column=0, padx=10, pady=10)
        self.amount_entry.grid(row=1, column=1, padx=10, pady=10)

        # Type
        self.type_label = customtkinter.CTkLabel(master=self, text="Type")
        self.type_select = customtkinter.CTkComboBox(master=self, values=["Income", "Expense"])
        self.type_select.set(entry["type"])
        self.type_label.grid(row=2, column=0, padx=10, pady=10)
        self.type_select.grid(row=2, column=1, padx=10, pady=10)

        # Category
        self.category_label = customtkinter.CTkLabel(master=self, text="Category")
        self.category_select = customtkinter.CTkComboBox(master=self, values=categories)
        self.category_select.set(entry["category"])
        self.category_label.grid(row=3, column=0, padx=10, pady=10)
        self.category_select.grid(row=3, column=1, padx=10, pady=10)

        # Account Type
        self.account_label = customtkinter.CTkLabel(master=self, text="Account")
        self.account_select = customtkinter.CTkComboBox(master=self, values=["Cash", "Bank Account", "Card"])
        self.account_select.set(entry["account_type"])
        self.account_label.grid(row=4, column=0, padx=10, pady=10)
        self.account_select.grid(row=4, column=1, padx=10, pady=10)

        # Submit Button
        self.submit_btn = customtkinter.CTkButton(master=self, text="Save Changes", command=self.submit)
        self.submit_btn.grid(row=5, column=0, columnspan=2, padx=10, pady=10)

    def submit(self):
        updated_data = {
            "unique_id": self.entry["unique_id"],  # Keep the same unique ID
            "amount": self.amount_entry.get(),
            "type": self.type_select.get(),
            "category": self.category_select.get(),
            "account_type": self.account_select.get()
        }
        self.callback(updated_data)  # Pass updated data to callback
        self.destroy()



money_manager = MoneyManagerApp()
money_manager.mainloop()
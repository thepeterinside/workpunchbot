import os
import subprocess

# Menu options
options = {
    "1": ("Welcome Mail", "WELCOME_EMAIL", "welcome.py"),
    "2": ("Deposit Mail", "DEPOSIT-MAIL", "deposit.py"),
    "3": ("Withdrawal Code", "WITHDRAWAL-CODE", "code.py"),
    "4": ("Withdrawal Mail", "WITHDRAW-MAIL", "withdraw.py"),
}

def show_menu():
    print("\nAvailable Operations:\n")
    for key, (name, _, _) in options.items():
        print(f"{key}. {name}")
    print()

def run_operation(choice):
    if choice in options:
        name, folder, script = options[choice]
        print(f"\n🚀 Running '{name}'...\n")
        path = os.path.join(folder, script)
        try:
            subprocess.run(["python", path], check=True)
        except subprocess.CalledProcessError as e:
            print(f"❌ Error running {name}: {e}")
    else:
        print("Invalid choice. Please try again.")

if __name__ == "__main__":
    show_menu()
    choice = input("Enter the number of the operation you want to run: ").strip()
    run_operation(choice)

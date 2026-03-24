# SharePay

SharePay is a free-to-use, Splitwise-style web application developed for the Sophomore Seminar. It provides a comprehensive platform for managing group expenses, tracking per-user balances, and easily settling debts.

## Features

* **Expense Tracking:** Log expenses with locations and optional tags.
* **Group Management:** Create groups and allow users to seamlessly join or leave.
* **Debt Splitting:** Automatically calculates equal splits among group members when an expense is added.
* **User Dashboards:** View outstanding splits, settled expenses, and overall group financial activity.
* **Receipt Uploads:** Attach and view receipt images or PDFs for specific expenses.

## Tech Stack

* **Backend:** Python, Flask, Flask-SQLAlchemy
* **Frontend:** HTML, CSS, Vanilla JavaScript (for basic UI toggles)
* **Database:** SQLite

## Project Structure

* `app.py`: Main application routing, database models, and logic.
* `templates/`: HTML templates for the frontend interface (e.g., `dashboard.html`).
* `static/`: Static assets and the `uploads/` directory for user-provided receipts.
* `requirements.txt`: Python dependencies required to run the application.

## Getting Started

### Prerequisites

Ensure you have Python installed on your system. 

### Installation

1. Clone the repository:
   ```bash
   git clone [https://github.com/abhizz11/Sophomore_Seminar.git](https://github.com/abhizz11/Sophomore_Seminar.git)
   cd Sophomore_Seminar
2. Install the required dependencies:
  ```bash
   pip install -r requirements.txt
   ```
3. Running the application
  ```bash
  python app.py
  ```
4. The application will be accessible locally, typically at http://127.0.0.1:5000/.

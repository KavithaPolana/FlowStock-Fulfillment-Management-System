# FlowStock – Fulfillment Management System

FlowStock is a web-based Fulfillment Management System designed to simplify and manage the complete order fulfillment process.

It helps businesses manage customer orders, warehouse allocation, shipments, inventory, and fulfillment exceptions through a centralized dashboard.

## 🚀 Features

- **Dashboard:** View important fulfillment statistics and recent activities.
- **Orders Management:** View, search, filter, and manage customer orders.
- **Warehouse Allocation:** Allocate orders to suitable warehouses.
- **Shipments & Tracking:** Create shipments and monitor delivery statuses.
- **Exception Management:** Identify and monitor fulfillment issues based on severity.
- **Warehouses & Inventory:** Monitor warehouse details, stock availability, and inventory levels.

## 🛠️ Technologies Used

### Frontend
- React.js
- Vite
- JavaScript
- CSS
- React Router DOM
- Lucide React Icons
- Axios (if used in API services)

### Backend
- Python
- Flask
- REST API

### Database
- MySQL

## 📁 Project Structure

```text
FlowStock/
│
├── backend/
│   ├── app.py
│   ├── database/
│   ├── routes/
│   ├── services/
│   └── requirements.txt
│
├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── components/
│   │   │   ├── Header.jsx
│   │   │   └── Sidebar.jsx
│   │   │
│   │   ├── pages/
│   │   │   ├── Dashboard.jsx
│   │   │   ├── Orders.jsx
│   │   │   ├── Allocation.jsx
│   │   │   ├── Shipments.jsx
│   │   │   ├── Exceptions.jsx
│   │   │   └── Warehouses.jsx
│   │   │
│   │   ├── services/
│   │   ├── App.jsx
│   │   ├── App.css
│   │   └── index.css
│   │
│   ├── package.json
│   └── vite.config.js
│
└── README.md
```

*Note: The structure above shows the main project folders. Your actual backend folders may contain additional modules.*

## ⚙️ Installation and Setup

### Prerequisites

Install the following before running the project:

- Python 3
- Node.js and npm
- MySQL Server
- Visual Studio Code

### 1. Clone the Repository

```bash
git clone <your-github-repository-url>
cd FlowStock
```

### 2. Database Setup

1. Start your MySQL Server.
2. Open MySQL Workbench.
3. Create the project database or import the provided SQL file.
4. Configure the database username, password, host, and database name in the backend configuration.

### 3. Backend Setup

Open a terminal and navigate to the backend folder:

```bash
cd backend
```

Create a virtual environment:

```bash
python -m venv venv
```

Activate the virtual environment on Windows:

```powershell
.\venv\Scripts\Activate.ps1
```

Install the required Python packages:

```bash
pip install -r requirements.txt
```

Start the Flask application:

```bash
python app.py
```

The backend will usually run at:

```text
http://127.0.0.1:5000
```

### 4. Frontend Setup

Open another terminal and navigate to the frontend folder:

```bash
cd frontend
```

Install the dependencies:

```bash
npm install
```

Start the React development server:

```bash
npm run dev
```

Open the frontend in your browser using the URL displayed in the terminal. By default:

```text
http://localhost:5173
```

## 🔄 Application Workflow

1. Customer orders are stored in the system.
2. Orders are reviewed through the Orders Management module.
3. Orders are allocated to suitable warehouses.
4. Shipments are created for allocated orders.
5. Shipment statuses are monitored through the tracking module.
6. Fulfillment exceptions are detected and reviewed.
7. Warehouse inventory and stock availability are monitored.

## 🎯 Project Objective

The main objective of FlowStock is to improve fulfillment visibility, simplify warehouse operations, track shipments, and identify operational issues through a centralized management platform.

## 👩‍💻 Author

**Kavitha Polana**

B.Tech – Artificial Intelligence and Machine Learning

## 📌 Project Status

Developed as a full-stack web application using React, Flask, and MySQL.
# Bora Inventory Management System (DMS)

A full-stack Inventory and Document Management System built to handle end-to-end stock tracking, Proforma Invoices (PI), Purchase Orders (PO), inward/outward logistics, and warehouse management.

## 🚀 Features

- **Inward & Outward Stock Tracking**: Track stock quantities as they arrive at warehouses and are dispatched.
- **Proforma Invoices (PI) & Purchase Orders (PO)**: Generate and manage billing, order quantities, and track dispatch plans.
- **Warehouse Management**: Track inventory accurately across multiple warehouses.
- **Export & Import Management**: Seamless handling of export invoices and direct exports, along with support for Excel/CSV data imports.
- **Low Stock Alerts**: Configurable alerts for low-stock products to prevent inventory shortages.
- **Real-time Stock Calculations**: Accurate, real-time calculation of available stock based on completed and pending dispatch plans.

## 🛠️ Technology Stack

**Frontend:**
- React.js (via Vite)
- Tailwind CSS for styling
- Axios for API communication

**Backend:**
- Python 3
- FastAPI framework
- MongoDB (with `motor` for async database operations)

## 📦 Project Structure

```text
Bora_DMS/
├── backend/                # FastAPI backend application
│   ├── server.py           # Main application entry point & API routes
│   └── ...                 # Other backend modules and configurations
├── frontend/               # React frontend application
│   ├── src/                # React source code (components, pages, utils)
│   └── package.json        # Frontend dependencies
└── tests/                  # Test suites
```

## ⚙️ Setup & Installation

### Backend Setup
1. Navigate to the backend directory:
   ```bash
   cd backend
   ```
2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use: venv\Scripts\activate
   ```
3. Install the dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Start the FastAPI server:
   ```bash
   uvicorn server:app --reload
   ```

### Frontend Setup
1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```
2. Install dependencies using npm or yarn:
   ```bash
   npm install
   ```
3. Start the development server:
   ```bash
   npm run dev
   ```

## 🧪 Testing

The project includes an automated test suite. To run the tests:
```bash
pytest
```

## 📝 License

This project is proprietary and confidential.

from fastapi import FastAPI, HTTPException, Request
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from supabase import create_client, Client
from datetime import datetime, date
import uvicorn
import json

# Supabase configuration
SUPABASE_URL = "https://gbkhkbfbarsnpbdkxzii.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imdia2hrYmZiYXJzbnBiZGt4emlpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzQzODAzNzMsImV4cCI6MjA0OTk1NjM3M30.mcOcC2GVEu_wD3xNBzSCC3MwDck3CIdmz4D8adU-bpI"

# Create Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Create FastAPI instance
app = FastAPI(
    title="Juan Gastos Dashboard",
    description="Dashboard for Juan's expenses with interactive graphs and CRUD operations",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup templates and static files
templates = Jinja2Templates(directory="templates")
try:
    app.mount("/static", StaticFiles(directory="static"), name="static")
except:
    print("Warning: 'static' folder not found. Static files won't be served.")

# Pydantic models
class Gasto(BaseModel):
    id: Optional[int] = None
    fecha: str  # Format: YYYY-MM-DD
    descripcion: str
    monto: float
    proyecto: str

class GastoCreate(BaseModel):
    fecha: str  # Format: YYYY-MM-DD
    descripcion: str
    monto: float
    proyecto: str

class GastoUpdate(BaseModel):
    fecha: Optional[str] = None
    descripcion: Optional[str] = None
    monto: Optional[float] = None
    proyecto: Optional[str] = None

# Root endpoint - serves the dashboard
@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})

# IMPORTANT: Put specific routes BEFORE dynamic routes
# API endpoint to get projects summary
@app.get("/api/gastos/summary")
async def get_gastos_summary():
    try:
        response = supabase.table("juan_gastos1").select("*").execute()
        data = response.data
        
        if not data:
            return {"projects": [], "total_records": 0, "total_amount": 0}
        
        # Group by project
        projects_summary = {}
        for item in data:
            proyecto = item["proyecto"]
            if proyecto not in projects_summary:
                projects_summary[proyecto] = {
                    "proyecto": proyecto,
                    "count": 0,
                    "total_amount": 0,
                    "avg_amount": 0,
                    "latest_date": None
                }
            
            projects_summary[proyecto]["count"] += 1
            projects_summary[proyecto]["total_amount"] += float(item["monto"])
            
            # Update latest date
            current_date = item["fecha"]
            if (projects_summary[proyecto]["latest_date"] is None or 
                current_date > projects_summary[proyecto]["latest_date"]):
                projects_summary[proyecto]["latest_date"] = current_date
        
        # Calculate averages
        for proyecto in projects_summary:
            projects_summary[proyecto]["avg_amount"] = (
                projects_summary[proyecto]["total_amount"] / 
                projects_summary[proyecto]["count"]
            )
        
        return {
            "projects": list(projects_summary.values()),
            "total_records": len(data),
            "total_amount": sum(float(item["monto"]) for item in data),
            "unique_projects": len(projects_summary)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching summary: {str(e)}")

# API endpoint to get gastos by date range
@app.get("/api/gastos/date-range")
async def get_gastos_by_date_range(start_date: str, end_date: str):
    try:
        # Validate date formats
        try:
            datetime.strptime(start_date, '%Y-%m-%d')
            datetime.strptime(end_date, '%Y-%m-%d')
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
        
        response = supabase.table("juan_gastos1").select("*").gte("fecha", start_date).lte("fecha", end_date).order("fecha", desc=True).execute()
        
        if response.data:
            return response.data
        else:
            return []
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching date range data: {str(e)}")

# API endpoint to get data for specific projects
@app.get("/api/gastos/filter")
async def get_gastos_filtered(projects: str):
    try:
        project_list = [p.strip() for p in projects.split(",")]
        
        response = supabase.table("juan_gastos1").select("*").in_("proyecto", project_list).order("fecha", desc=True).execute()
        
        if response.data:
            return response.data
        else:
            return []
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching filtered data: {str(e)}")

# API endpoint to get all gastos
@app.get("/api/gastos", response_model=List[Dict[str, Any]])
async def get_gastos():
    try:
        response = supabase.table("juan_gastos1").select("*").order("fecha", desc=True).execute()
        
        if response.data:
            return response.data
        else:
            return []
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching data: {str(e)}")

# API endpoint to get a specific gasto by ID
@app.get("/api/gastos/{gasto_id}")
async def get_gasto(gasto_id: int):
    try:
        response = supabase.table("juan_gastos1").select("*").eq("id", gasto_id).execute()
        
        if not response.data:
            raise HTTPException(status_code=404, detail="Expense record not found")
        
        return response.data[0]
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching expense: {str(e)}")

# API endpoint to create a new gasto
@app.post("/api/gastos", response_model=Dict[str, Any])
async def create_gasto(gasto: GastoCreate):
    try:
        # Validate date format
        try:
            datetime.strptime(gasto.fecha, '%Y-%m-%d')
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
        
        # Validate proyecto length (max 20 characters as per table constraint)
        if len(gasto.proyecto) > 20:
            raise HTTPException(status_code=400, detail="Project name must be 20 characters or less")
        
        response = supabase.table("juan_gastos1").insert({
            "fecha": gasto.fecha,
            "descripcion": gasto.descripcion,
            "monto": gasto.monto,
            "proyecto": gasto.proyecto
        }).execute()
        
        if response.data:
            return {"message": "Expense created successfully", "data": response.data[0]}
        else:
            raise HTTPException(status_code=500, detail="Failed to create expense")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating expense: {str(e)}")

# API endpoint to update a gasto
@app.put("/api/gastos/{gasto_id}")
async def update_gasto(gasto_id: int, gasto: GastoUpdate):
    try:
        # Check if the record exists
        existing = supabase.table("juan_gastos1").select("*").eq("id", gasto_id).execute()
        if not existing.data:
            raise HTTPException(status_code=404, detail="Expense record not found")
        
        # Build update data (only include non-None fields)
        update_data = {}
        if gasto.fecha is not None:
            # Validate date format
            try:
                datetime.strptime(gasto.fecha, '%Y-%m-%d')
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
            update_data["fecha"] = gasto.fecha
        
        if gasto.descripcion is not None:
            update_data["descripcion"] = gasto.descripcion
        
        if gasto.monto is not None:
            update_data["monto"] = gasto.monto
        
        if gasto.proyecto is not None:
            if len(gasto.proyecto) > 20:
                raise HTTPException(status_code=400, detail="Project name must be 20 characters or less")
            update_data["proyecto"] = gasto.proyecto
        
        if not update_data:
            raise HTTPException(status_code=400, detail="No fields provided for update")
        
        response = supabase.table("juan_gastos1").update(update_data).eq("id", gasto_id).execute()
        
        if response.data:
            return {"message": "Expense updated successfully", "data": response.data[0]}
        else:
            raise HTTPException(status_code=500, detail="Failed to update expense")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating expense: {str(e)}")

# API endpoint to delete a gasto
@app.delete("/api/gastos/{gasto_id}")
async def delete_gasto(gasto_id: int):
    try:
        # Check if the record exists
        existing = supabase.table("juan_gastos1").select("*").eq("id", gasto_id).execute()
        if not existing.data:
            raise HTTPException(status_code=404, detail="Expense record not found")
        
        response = supabase.table("juan_gastos1").delete().eq("id", gasto_id).execute()
        
        return {"message": "Expense deleted successfully", "deleted_id": gasto_id}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting expense: {str(e)}")

# Health check endpoint
@app.get("/api/health")
async def health_check():
    try:
        # Test Supabase connection
        response = supabase.table("juan_gastos1").select("count", count="exact").limit(1).execute()
        return {
            "status": "healthy",
            "database": "connected",
            "table": "juan_gastos1",
            "total_records": response.count
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "database": "disconnected",
            "error": str(e)
        }

# Add sample data endpoint
@app.post("/api/gastos/sample-data")
async def add_sample_data():
    """Add sample expense data for testing"""
    try:
        sample_data = [
            {
                "fecha": "2024-01-15",
                "descripcion": "Seeds and supplies for berry farming",
                "monto": 1250.50,
                "proyecto": "berries"
            },
            {
                "fecha": "2024-01-20",
                "descripcion": "Irrigation system installation",
                "monto": 3200.00,
                "proyecto": "berries"
            },
            {
                "fecha": "2024-02-01",
                "descripcion": "Tomato seedlings purchase",
                "monto": 890.75,
                "proyecto": "tomate"
            },
            {
                "fecha": "2024-02-15",
                "descripcion": "Jalapeño seeds and fertilizer",
                "monto": 445.25,
                "proyecto": "jalapeño"
            },
            {
                "fecha": "2024-03-01",
                "descripcion": "Greenhouse maintenance",
                "monto": 750.00,
                "proyecto": "berries"
            }
        ]
        
        response = supabase.table("juan_gastos1").insert(sample_data).execute()
        
        if response.data:
            return {"message": "Sample data added successfully", "records_added": len(response.data)}
        else:
            raise HTTPException(status_code=500, detail="Failed to add sample data")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error adding sample data: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
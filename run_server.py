import sys
import os

# Redirect output to file
log_file = open('server_output.log', 'w', buffering=1)
sys.stdout = log_file
sys.stderr = log_file

print("=" * 60)
print("Starting Food Delivery Platform Server")
print("=" * 60)
print()

try:
    import uvicorn
    print("✓ Uvicorn imported")

    print("✓ Starting server on http://0.0.0.0:8000")
    print("✓ API Docs: http://localhost:8000/docs")
    print("✓ Dashboard: http://localhost:8000/api/v1/dashboard/")
    print()
    print("Server is running... (Check http://localhost:8000/docs)")
    print()

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
finally:
    log_file.close()


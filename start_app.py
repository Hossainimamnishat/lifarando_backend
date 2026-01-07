#!/usr/bin/env python
"""
Startup script for Food Delivery Platform
"""
import uvicorn
import sys

if __name__ == "__main__":
    print("=" * 60)
    print("🚀 Starting Food Delivery Platform...")
    print("=" * 60)
    print()
    print("📍 Server will be available at:")
    print("   - Local: http://localhost:8000")
    print("   - Network: http://0.0.0.0:8000")
    print("   - API Docs: http://localhost:8000/docs")
    print("   - Dashboard: http://localhost:8000/api/v1/dashboard/")
    print()
    print("Press CTRL+C to stop the server")
    print("=" * 60)
    print()

    try:
        uvicorn.run(
            "app.main:app",
            host="0.0.0.0",
            port=8000,
            reload=True,
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\n\n👋 Server stopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n\n❌ Error starting server: {e}")
        sys.exit(1)


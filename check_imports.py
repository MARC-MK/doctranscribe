"""Check if the handwriting router can be imported."""
try:
    from backend.app.routers import handwriting
    print("Successfully imported handwriting router")
    print(f"Router prefix: {handwriting.router.prefix}")
    print(f"Router routes: {[route.path for route in handwriting.router.routes]}")
except ImportError as e:
    print(f"Error importing handwriting router: {e}")
    import traceback
    traceback.print_exc() 
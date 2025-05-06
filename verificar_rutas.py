import requests
import sys
import time
from colorama import init, Fore, Style

# Inicializar colorama para colores en la consola
init()

def print_color(text, color=Fore.WHITE, style=Style.NORMAL):
    """Imprimir texto con color en la consola"""
    print(f"{style}{color}{text}{Style.RESET_ALL}")

def check_route(url, expected_status=200, description=""):
    """Verificar si una ruta está funcionando correctamente"""
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == expected_status:
            print_color(f"[OK] {description} ({url}) - Status: {response.status_code}", Fore.GREEN)
            return True
        else:
            print_color(f"[ERROR] {description} ({url}) - Status: {response.status_code} (Esperado: {expected_status})", Fore.RED)
            return False
    except requests.exceptions.RequestException as e:
        print_color(f"[ERROR] {description} ({url}) - Error: {str(e)}", Fore.RED, Style.BRIGHT)
        return False

def main():
    # Verificar que el servidor esté en ejecución
    base_url = "http://127.0.0.1:5000"
    
    print_color("\n=== VERIFICACIÓN DE RUTAS DE LA AGENCIA DE AUTOS ===\n", Fore.CYAN, Style.BRIGHT)
    
    print_color("Verificando que el servidor esté en ejecución...", Fore.YELLOW)
    server_running = check_route(base_url, description="Servidor principal")
    
    if not server_running:
        print_color("\n⚠️ El servidor no está en ejecución. Por favor, inicia la aplicación con:", Fore.RED, Style.BRIGHT)
        print_color("   python app_final.py", Fore.YELLOW)
        return
    
    print_color("\n--- Rutas públicas ---", Fore.CYAN)
    routes = [
        {"url": f"{base_url}/login", "description": "Página de login"},
        {"url": f"{base_url}/autos", "description": "Listado de autos"},
    ]
    
    public_success = 0
    for route in routes:
        if check_route(route["url"], description=route["description"]):
            public_success += 1
    
    print_color(f"\nRutas públicas: {public_success}/{len(routes)} funcionando correctamente", 
                Fore.GREEN if public_success == len(routes) else Fore.YELLOW)
    
    print_color("\n--- Rutas protegidas (requieren autenticación) ---", Fore.CYAN)
    protected_routes = [
        {"url": f"{base_url}/dashboard", "description": "Dashboard", "expected": 200},  # Debería mostrar el dashboard o login
        {"url": f"{base_url}/ventas", "description": "Listado de ventas", "expected": 200},
        {"url": f"{base_url}/usuarios", "description": "Gestión de usuarios", "expected": 200},
        {"url": f"{base_url}/estadisticas", "description": "Estadísticas", "expected": 200},
        {"url": f"{base_url}/autos/nuevo", "description": "Nuevo auto", "expected": 200},
    ]
    
    protected_success = 0
    for route in protected_routes:
        expected = route.get("expected", 200)
        if check_route(route["url"], expected_status=expected, description=route["description"]):
            protected_success += 1
    
    print_color(f"\nRutas protegidas: {protected_success}/{len(protected_routes)} funcionando correctamente", 
                Fore.GREEN if protected_success == len(protected_routes) else Fore.YELLOW)
    
    # Resumen
    total_routes = len(routes) + len(protected_routes)
    total_success = public_success + protected_success
    
    print_color("\n=== RESUMEN ===", Fore.CYAN, Style.BRIGHT)
    print_color(f"Total de rutas verificadas: {total_routes}", Fore.WHITE)
    print_color(f"Rutas funcionando correctamente: {total_success}", 
                Fore.GREEN if total_success == total_routes else Fore.YELLOW)
    
    if total_success == total_routes:
        print_color("\n[EXITO] ¡Todas las rutas están funcionando correctamente!", Fore.GREEN, Style.BRIGHT)
    else:
        print_color(f"\n[ADVERTENCIA] {total_routes - total_success} rutas no están funcionando como se esperaba.", Fore.RED, Style.BRIGHT)
        print_color("Revisa los mensajes anteriores para más detalles.", Fore.YELLOW)
    
    print_color("\nPara pruebas más exhaustivas, sigue la lista de verificación en pruebas_manuales.md", Fore.CYAN)

if __name__ == "__main__":
    main()

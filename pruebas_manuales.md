# Plan de Pruebas Manuales - Agencia de Autos

## 1. Autenticación

- [ ] **Iniciar sesión**
  - Acceder a `/login`
  - Ingresar usuario: `admin` y contraseña: `admin123`
  - Verificar redirección al dashboard
  - Verificar mensaje de bienvenida

- [ ] **Iniciar sesión con credenciales incorrectas**
  - Acceder a `/login`
  - Ingresar credenciales incorrectas
  - Verificar mensaje de error

- [ ] **Cerrar sesión**
  - Hacer clic en "Cerrar sesión"
  - Verificar redirección a la página de login
  - Verificar mensaje de confirmación

## 2. Dashboard

- [ ] **Acceso al dashboard**
  - Verificar que se muestra correctamente después de iniciar sesión
  - Comprobar que muestra estadísticas básicas (autos disponibles)
  - Comprobar que muestra los últimos autos agregados

## 3. Gestión de Autos

- [ ] **Listar autos**
  - Acceder a `/autos`
  - Verificar que se muestran todos los autos
  - Comprobar que se muestran correctamente las imágenes y precios

- [ ] **Ver detalle de auto**
  - Hacer clic en un auto específico
  - Verificar que se muestra toda la información del auto
  - Comprobar que se muestran las imágenes

- [ ] **Agregar nuevo auto**
  - Acceder a `/autos/nuevo`
  - Completar el formulario con datos válidos
  - Subir imágenes (opcional)
  - Enviar el formulario
  - Verificar mensaje de confirmación
  - Comprobar que el auto aparece en el listado

- [ ] **Editar auto**
  - Acceder a la edición de un auto existente
  - Modificar algunos campos
  - Guardar cambios
  - Verificar mensaje de confirmación
  - Comprobar que los cambios se reflejan en el detalle del auto

## 4. Gestión de Ventas

- [ ] **Listar ventas**
  - Acceder a `/ventas`
  - Verificar que se muestran todas las ventas
  - Probar filtros (por mes, año, estado)

- [ ] **Registrar nueva venta**
  - Acceder a `/ventas/registrar`
  - Seleccionar un auto disponible
  - Completar datos del cliente
  - Registrar la venta
  - Verificar mensaje de confirmación
  - Comprobar que la venta aparece en el listado
  - Verificar que el auto ahora aparece como vendido

- [ ] **Ver detalle de venta**
  - Hacer clic en una venta específica
  - Verificar que se muestra toda la información

- [ ] **Marcar venta como pagada**
  - Acceder al detalle de una venta con estado "Señado"
  - Marcar como pagada
  - Verificar cambio de estado
  - Comprobar fecha de pago

## 5. Gestión de Usuarios

- [ ] **Listar usuarios**
  - Acceder a `/usuarios`
  - Verificar que se muestran todos los usuarios

- [ ] **Crear nuevo usuario**
  - Completar formulario de nuevo usuario
  - Crear usuario
  - Verificar mensaje de confirmación
  - Comprobar que el usuario aparece en el listado

- [ ] **Editar usuario**
  - Acceder a la edición de un usuario existente
  - Modificar algunos campos
  - Guardar cambios
  - Verificar mensaje de confirmación

- [ ] **Eliminar usuario**
  - Seleccionar un usuario para eliminar
  - Confirmar eliminación
  - Verificar mensaje de confirmación
  - Comprobar que el usuario ya no aparece en el listado

## 6. Estadísticas

- [ ] **Ver estadísticas**
  - Acceder a `/estadisticas`
  - Verificar que se muestran gráficos y datos
  - Comprobar que los datos son coherentes con las ventas registradas

## 7. Pruebas de Seguridad

- [ ] **Acceso a rutas protegidas sin autenticación**
  - Cerrar sesión
  - Intentar acceder directamente a `/dashboard`, `/ventas`, `/usuarios`, etc.
  - Verificar redirección a login

- [ ] **Acceso a rutas de administrador con usuario vendedor**
  - Iniciar sesión con un usuario vendedor
  - Intentar acceder a `/usuarios`, `/estadisticas`
  - Verificar mensaje de error o redirección

## 8. Pruebas de Interfaz

- [ ] **Responsive design**
  - Probar la aplicación en diferentes tamaños de pantalla
  - Verificar que la interfaz se adapta correctamente

- [ ] **Navegación**
  - Verificar que todos los enlaces del menú funcionan correctamente
  - Comprobar que las migas de pan (breadcrumbs) funcionan

## 9. Pruebas de Filtros y Formato

- [ ] **Filtro formato_precio**
  - Verificar que los precios se muestran correctamente formateados en todas las vistas
  - Comprobar separadores de miles y decimales

## Instrucciones para completar las pruebas

1. Marca cada ítem como completado [x] cuando hayas verificado que funciona correctamente
2. Si encuentras algún problema, anótalo debajo del ítem correspondiente
3. Para cada problema encontrado, registra:
   - Descripción del problema
   - Pasos para reproducirlo
   - Comportamiento esperado vs. comportamiento actual
   - Capturas de pantalla (si es posible)

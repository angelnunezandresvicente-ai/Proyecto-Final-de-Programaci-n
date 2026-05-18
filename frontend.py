"""
SISTEMA DE GESTIÓN DE FARMACIA - INTERFAZ GRÁFICA (FRONTEND)
==============================================================
Módulo de interfaz de usuario usando CustomTkinter.

Implementa tres interfaces diferentes según el rol del usuario:
1. FARMACEUTA: Gestión de inventario y medicamentos
2. VENDEDOR: Punto de venta y carrito de compras
3. GERENTE: Reportes y análisis de ventas

Características:
- Interfaz oscura moderna (tema dark)
- Validaciones en tiempo real
- Manejo robusto de errores
- Generación de recibos en formato texto
"""

import customtkinter as ctk
from backend import (
    SistemaAutenticacion, ServicioMedicamentos, ServicioVentas,
    RepositorioUsuariosCSV, RepositorioMedicamentosCSV, RepositorioVentasCSV
)
from tkinter import ttk, messagebox
import os
from datetime import datetime

# ============================================================
# CONFIGURACIÓN GLOBAL DE COLORES Y TEMAS
# ============================================================

# Paleta de colores utilizada en toda la aplicación
COLOR_FONDO = "#0f172a"          # Fondo principal oscuro (azul muy oscuro)
COLOR_BOTON = "#002366"          # Botones primarios (azul)
COLOR_BOTON_HOVER = "#003bba"    # Botones al pasar mouse (azul más claro)
COLOR_EXITO = "#10b981"          # Éxito y confirmación (verde)
COLOR_PELIGRO = "#ef4444"        # Peligro y eliminar (rojo)
COLOR_ADVERTENCIA = "#f59e0b"    # Advertencias (ámbar)

# Configurar tema global de CustomTkinter
ctk.set_appearance_mode("Dark")           # Modo oscuro
ctk.set_default_color_theme("blue")       # Tema de color azul

# ============================================================
# INSTANCIAS GLOBALES DE REPOSITORIOS Y SERVICIOS
# ============================================================

# Repositorios: acceden a los archivos CSV
repo_usuarios = RepositorioUsuariosCSV()
repo_meds = RepositorioMedicamentosCSV()
repo_ventas = RepositorioVentasCSV()

# Servicios: lógica de negocio
auth_sys = SistemaAutenticacion(repositorio_usuarios=repo_usuarios)
servicio_meds = ServicioMedicamentos(repo_meds)
servicio_ventas = ServicioVentas(repo_ventas, repo_meds)

# ============================================================
# FUNCIONES AUXILIARES
# ============================================================

def limpiar_pantalla(ventana):
    """
    Elimina todos los widgets de una ventana.
    
    Se usa para cambiar de pantalla (login -> dashboard).
    Limpia todos los elementos visuales para mostrar la siguiente interfaz.
    
    Args:
        ventana (CTkFrame): Ventana principal a limpiar
    """
    for widget in ventana.winfo_children():
        widget.destroy()

# ============================================================
# PANTALLA 1: LOGIN
# ============================================================

def mostrar_pantalla_login(ventana):
    """
    Muestra la interfaz de autenticación.
    
    Características:
    - Campo de usuario y contraseña
    - Validación de campos no vacíos
    - Protección contra fuerza bruta (3 intentos, bloqueo 15 min)
    - Mensajes de error descriptivos
    - Redirección según rol del usuario
    
    Args:
        ventana (CTkFrame): Ventana principal
    """
    limpiar_pantalla(ventana)
    ventana.title("Farmacia Dr Clara - Login")
    ventana.geometry("600x700")

    # Frame contenedor principal con bordes redondeados
    frame = ctk.CTkFrame(ventana, corner_radius=20, fg_color="#1e293b")
    frame.place(relx=0.5, rely=0.5, anchor=ctk.CENTER)

    # Logo y título
    ctk.CTkLabel(
        frame, 
        text="Farmacia Dr Clara", 
        font=("Roboto", 26, "bold"), 
        text_color="white"
    ).pack(pady=(30, 10))
    
    ctk.CTkLabel(frame, text="💊", font=("Roboto", 80)).pack(pady=15)

    # Campos de entrada
    entry_usuario = ctk.CTkEntry(
        frame, 
        placeholder_text="Usuario", 
        width=280, 
        height=40
    )
    entry_usuario.pack(pady=10)

    entry_password = ctk.CTkEntry(
        frame, 
        placeholder_text="Contraseña", 
        show="*",  # Ocultar caracteres
        width=280, 
        height=40
    )
    entry_password.pack(pady=10)

    # Label para mostrar errores
    label_error = ctk.CTkLabel(
        frame, 
        text="", 
        text_color=COLOR_PELIGRO, 
        font=("Roboto", 12)
    )
    label_error.pack(pady=5)

    def evento_login():
        """
        Maneja el evento de click en botón Ingresar.
        
        Proceso:
        1. Obtiene usuario y contraseña
        2. Valida que no estén vacíos
        3. Autentica contra el sistema
        4. Redirige a la pantalla según rol o muestra error
        """
        usuario = entry_usuario.get().strip()
        password = entry_password.get().strip()
        
        # Validar campos no vacíos
        if not usuario or not password:
            label_error.configure(text="❌ Usuario y contraseña requeridos")
            return
        
        # Llamar al sistema de autenticación
        exito, rol, error = auth_sys.autenticar(usuario, password)

        if exito:
            # Login exitoso: mostrar pantalla según rol
            if rol == "farmaceuta": 
                mostrar_pantalla_farmaceuta(ventana, usuario)
            elif rol == "gerente": 
                mostrar_pantalla_gerente(ventana, usuario)
            elif rol == "vendedor": 
                mostrar_pantalla_vendedor(ventana, usuario)
        else:
            # Login fallido: mostrar mensaje de error
            label_error.configure(text=f"❌ {error}")

    # Botón de ingresar
    ctk.CTkButton(
        frame, 
        text="Ingresar", 
        width=280, 
        height=45, 
        fg_color=COLOR_BOTON, 
        hover_color=COLOR_BOTON_HOVER, 
        font=("Roboto", 16, "bold"), 
        command=evento_login
    ).pack(pady=(20, 30))


# ============================================================
# PANTALLA 2: FARMACEUTA (Gestión de Inventario)
# ============================================================

def mostrar_pantalla_farmaceuta(ventana, nombre_usuario):
    """
    Interfaz para farmacéuticos: gestión de medicamentos.
    
    Funcionalidades:
    - Registrar nuevos medicamentos con validaciones
    - Ver inventario completo en tabla
    - Buscar medicamentos por nombre
    - Eliminar medicamentos
    - Ver alertas de medicamentos próximos a caducar
    
    Validaciones implementadas:
    - Nombre: mínimo 3 caracteres
    - Marca: mínimo 2 caracteres
    - Precio: mayor a $0
    - Fecha: formato YYYY-MM-DD, futuro
    - Stock: número no negativo
    - Duplicados: no permite medicamentos idénticos
    
    Args:
        ventana (CTkFrame): Ventana principal
        nombre_usuario (str): Nombre del farmacéutico logueado
    """
    limpiar_pantalla(ventana)
    ventana.title(f"Farmaceuta - {nombre_usuario}")
    ventana.geometry("1200x800")
    # Maximizar ventana si es Windows
    ventana.after(0, lambda: ventana.state('zoomed') if os.name == 'nt' else None)

    # ========== HEADER ==========
    frame_header = ctk.CTkFrame(ventana, fg_color="#1e293b", height=60)
    frame_header.pack(fill="x")
    frame_header.pack_propagate(False)

    ctk.CTkLabel(
        frame_header, 
        text=f"💊 Farmaceuta: {nombre_usuario}", 
        font=("Roboto", 18, "bold"), 
        text_color="#3b82f6"
    ).pack(side="left", padx=20, pady=15)

    # ========== BODY ==========
    frame_body = ctk.CTkFrame(ventana, fg_color="#0f172a")
    frame_body.pack(fill="both", expand=True, padx=20, pady=20)

    # ========== FORMULARIO DE REGISTRO ==========
    frame_form = ctk.CTkFrame(frame_body, fg_color="#1e293b", corner_radius=12)
    frame_form.pack(fill="x", pady=10)

    ctk.CTkLabel(
        frame_form, 
        text="📝 Registrar Medicamento", 
        font=("Roboto", 14, "bold"), 
        text_color="#3b82f6"
    ).pack(pady=(10, 15))

    # Grid con campos de entrada
    form_grid = ctk.CTkFrame(frame_form, fg_color="transparent")
    form_grid.pack(padx=15, pady=10)

    # Fila 1: Nombre, Marca, Precio
    entry_nombre = ctk.CTkEntry(form_grid, placeholder_text="Nombre", width=200)
    entry_nombre.grid(row=0, column=0, padx=5, pady=10)
    
    entry_marca = ctk.CTkEntry(form_grid, placeholder_text="Marca", width=150)
    entry_marca.grid(row=0, column=1, padx=5, pady=10)
    
    entry_precio = ctk.CTkEntry(form_grid, placeholder_text="Precio", width=100)
    entry_precio.grid(row=0, column=2, padx=5, pady=10)
    
    # Fila 2: Presentación, Fecha, Precio Unitario
    entry_cantidad = ctk.CTkEntry(form_grid, placeholder_text="Pres. (ej: 500ml)", width=120)
    entry_cantidad.grid(row=1, column=0, padx=5, pady=10)
    
    entry_fecha = ctk.CTkEntry(form_grid, placeholder_text="Caducidad (YYYY-MM-DD)", width=160)
    entry_fecha.grid(row=1, column=1, padx=5, pady=10)
    
    entry_precio_ind = ctk.CTkEntry(form_grid, placeholder_text="Precio unitario", width=130)
    entry_precio_ind.grid(row=1, column=2, padx=5, pady=10)

    # Fila 3: Stock y Checkbox Receta
    entry_stock = ctk.CTkEntry(form_grid, placeholder_text="Stock Inicial", width=120)
    entry_stock.grid(row=2, column=0, padx=5, pady=10)
    
    check_var = ctk.StringVar(value="off")
    check_receta = ctk.CTkCheckBox(
        form_grid, 
        text="Requiere Receta", 
        variable=check_var, 
        onvalue="on", 
        offvalue="off"
    )
    check_receta.grid(row=2, column=1, padx=5, pady=10)

    # ========== TABLA DE MEDICAMENTOS ==========
    frame_tabla = ctk.CTkFrame(frame_body, fg_color="#1e293b", corner_radius=12)
    frame_tabla.pack(fill="both", expand=True, pady=10)

    ctk.CTkLabel(
        frame_tabla, 
        text="📋 Medicamentos en Inventario", 
        font=("Roboto", 14, "bold"), 
        text_color="#facc15"
    ).pack(pady=(10, 10))

    # Crear tabla con columnas
    cols = ("ID", "Nombre", "Marca", "Pres.", "Precio", "Stock", "Receta", "Caducidad")
    tabla = ttk.Treeview(frame_tabla, columns=cols, show="headings", height=12)
    
    # Configurar headers
    for col in cols: 
        tabla.heading(col, text=col)
    
    # Ajustar anchos de columnas
    tabla.column("ID", width=50)
    tabla.column("Nombre", width=200)
    tabla.column("Marca", width=100)
    tabla.column("Pres.", width=80)
    tabla.column("Precio", width=80)
    tabla.column("Stock", width=60)
    tabla.column("Receta", width=60)
    tabla.column("Caducidad", width=100)
    
    tabla.pack(fill="both", expand=True, padx=15, pady=10)

    def actualizar_tabla():
        """
        Recarga la tabla con todos los medicamentos del inventario.
        
        Se llama después de:
        - Registrar nuevo medicamento
        - Eliminar medicamento
        - Limpiar búsqueda
        """
        for item in tabla.get_children(): 
            tabla.delete(item)
        
        for med in repo_meds.obtener_todos():
            req_receta = "Sí" if med.requiere_receta else "No"
            tabla.insert(
                "", "end", 
                values=(
                    med.id_medicamento, 
                    med.nombre, 
                    med.marca, 
                    med.cantidad, 
                    f"${med.precio_individual:.2f}", 
                    med.stock, 
                    req_receta, 
                    med.fecha_caducidad
                )
            )

    def guardar_medicamento():
        """
        Valida y registra un nuevo medicamento.
        
        Proceso:
        1. Obtiene valores de los entry fields
        2. Valida que no estén vacíos
        3. Llama al servicio para registrar (con validaciones)
        4. Muestra éxito o error
        5. Limpia formulario y recarga tabla
        
        Las validaciones exhaustivas están en ServicioMedicamentos.registrar_medicamento()
        """
        nombre = entry_nombre.get().strip()
        marca = entry_marca.get().strip()
        precio = entry_precio.get().strip()
        cantidad = entry_cantidad.get().strip()
        fecha = entry_fecha.get().strip()
        precio_ind = entry_precio_ind.get().strip()
        stock_val = entry_stock.get().strip()
        
        # Validar campos requeridos
        if not all([nombre, marca, precio, cantidad, fecha, stock_val]):
            messagebox.showwarning(
                "Atención", 
                "Completa todos los campos obligatorios."
            )
            return

        try:
            # Llamar al servicio con todas las validaciones
            servicio_meds.registrar_medicamento(
                nombre=nombre, 
                precio=float(precio), 
                cantidad=cantidad, 
                fecha_caducidad=fecha, 
                marca=marca,
                precio_individual=float(precio_ind) if precio_ind else float(precio),
                stock=int(stock_val), 
                requiere_receta=(check_var.get() == "on")
            )
            
            messagebox.showinfo(
                "✓ Éxito", 
                "Medicamento registrado exitosamente."
            )
            
            # Limpiar formulario
            for e in (entry_nombre, entry_marca, entry_precio, entry_cantidad, 
                     entry_fecha, entry_precio_ind, entry_stock):
                e.delete(0, "end")
            check_var.set("off")
            
            # Recargar tabla
            actualizar_tabla()
            
        except ValueError as e:
            messagebox.showerror("❌ Error", str(e))
        except Exception as e:
            messagebox.showerror(
                "❌ Error Inesperado", 
                f"No se pudo guardar el medicamento: {str(e)}"
            )

    def eliminar_medicamento():
        """
        Elimina el medicamento seleccionado de la tabla.
        
        Proceso:
        1. Verifica que hay un medicamento seleccionado
        2. Pide confirmación al usuario
        3. Elimina del repositorio
        4. Recarga tabla
        """
        sel = tabla.selection()
        if not sel: 
            return messagebox.showwarning(
                "Atención", 
                "Selecciona un medicamento"
            )
        
        id_med = tabla.item(sel[0])["values"][0]
        
        if messagebox.askyesno("Confirmar", f"¿Eliminar medicamento {id_med}?"):
            try:
                servicio_meds.eliminar_medicamento(id_med)
                actualizar_tabla()
                messagebox.showinfo(
                    "✓ Éxito", 
                    "Medicamento eliminado correctamente"
                )
            except Exception as e:
                messagebox.showerror("❌ Error", str(e))

    def buscar_medicamento():
        """
        Busca medicamentos por nombre (búsqueda parcial).
        
        Proceso:
        1. Obtiene término de búsqueda
        2. Si está vacío, muestra todos
        3. Si no, filtra medicamentos que contengan el término
        4. Actualiza la tabla dinámicamente
        """
        termino = entry_nombre.get().strip()
        
        # Limpiar tabla
        for item in tabla.get_children(): 
            tabla.delete(item)
        
        # Si no hay término, mostrar todos
        if not termino: 
            return actualizar_tabla()
        
        try:
            # Buscar medicamentos
            for med in servicio_meds.buscar_medicamentos(nombre=termino):
                req_receta = "Sí" if med.requiere_receta else "No"
                tabla.insert(
                    "", "end", 
                    values=(
                        med.id_medicamento, 
                        med.nombre, 
                        med.marca, 
                        med.cantidad, 
                        f"${med.precio_individual:.2f}", 
                        med.stock, 
                        req_receta, 
                        med.fecha_caducidad
                    )
                )
        except ValueError as e:
            messagebox.showwarning("Búsqueda", str(e))
            actualizar_tabla()

    def ver_caducidades():
        """
        Abre ventana con alertas de medicamentos próximos a caducar.
        
        Muestra medicamentos que vencen en los próximos 30 días.
        Útil para farmacéuticos en revisiones de inventario.
        """
        try:
            meds = servicio_meds.obtener_proximos_a_caducar(30)
            
            # Crear ventana modal
            top = ctk.CTkToplevel(ventana)
            top.title("Alertas de Caducidad")
            top.geometry("600x400")
            top.transient(ventana)  # Ventana modal
            
            # Título
            ctk.CTkLabel(
                top, 
                text="⚠️ Medicamentos por vencer (Próximos 30 días)", 
                font=("Roboto", 16, "bold"), 
                text_color=COLOR_PELIGRO
            ).pack(pady=10)
            
            # Si no hay medicamentos por caducar
            if not meds:
                ctk.CTkLabel(
                    top, 
                    text="✓ No hay medicamentos próximos a vencer.", 
                    font=("Roboto", 14), 
                    text_color=COLOR_EXITO
                ).pack(pady=20)
                return
                
            # Tabla de medicamentos próximos a caducar
            frame_t = ctk.CTkFrame(top)
            frame_t.pack(fill="both", expand=True, padx=10, pady=10)
            
            c = ("ID", "Nombre", "Caducidad", "Stock")
            tv = ttk.Treeview(frame_t, columns=c, show="headings")
            for col in c: 
                tv.heading(col, text=col)
            tv.pack(fill="both", expand=True)
            
            for m in meds: 
                tv.insert(
                    "", "end", 
                    values=(m.id_medicamento, m.nombre, m.fecha_caducidad, m.stock)
                )
        except Exception as e:
            messagebox.showerror("❌ Error", str(e))

    # ========== BOTONES DE ACCIÓN ==========
    frame_botones = ctk.CTkFrame(form_grid, fg_color="transparent")
    frame_botones.grid(row=3, column=0, columnspan=3, pady=10)

    ctk.CTkButton(
        frame_botones, 
        text="💾 Guardar", 
        fg_color=COLOR_EXITO, 
        command=guardar_medicamento
    ).pack(side="left", padx=5)
    
    ctk.CTkButton(
        frame_botones, 
        text="🔍 Buscar", 
        fg_color=COLOR_BOTON, 
        command=buscar_medicamento
    ).pack(side="left", padx=5)
    
    ctk.CTkButton(
        frame_botones, 
        text="🗑️ Eliminar", 
        fg_color=COLOR_PELIGRO, 
        command=eliminar_medicamento
    ).pack(side="left", padx=5)
    
    ctk.CTkButton(
        frame_botones, 
        text="⚠️ Alertas Caducidad", 
        fg_color=COLOR_ADVERTENCIA, 
        text_color="black", 
        command=ver_caducidades
    ).pack(side="left", padx=5)

    # Cargar tabla inicial
    actualizar_tabla()
    
    # Botón de cierre de sesión
    ctk.CTkButton(
        ventana, 
        text="Cerrar Sesión", 
        fg_color=COLOR_PELIGRO, 
        font=("Roboto", 14, "bold"), 
        command=lambda: mostrar_pantalla_login(ventana)
    ).pack(pady=20)


# ============================================================
# PANTALLA 3: VENDEDOR (Punto de Venta)
# ============================================================

def mostrar_pantalla_vendedor(ventana, nombre_usuario):
    """
    Interfaz de punto de venta para vendedores.
    
    Layout: Dos columnas:
    - Izquierda: Catálogo de medicamentos con búsqueda y filtros
    - Derecha: Carrito de compras
    
    Funcionalidades:
    - Catálogo de medicamentos con cards visuales
    - Búsqueda dinámica por nombre
    - Filtros: Todos, Con Stock, Sin Receta
    - Indicadores visuales (rojo si sin stock)
    - Validación de medicamentos con receta (requiere datos)
    - Carrito con modificación de cantidades
    - Cálculo automático de total
    - Generación de recibo en formato texto
    - Persisten cambios de stock en CSV
    
    Args:
        ventana (CTkFrame): Ventana principal
        nombre_usuario (str): Nombre del vendedor
    """
    limpiar_pantalla(ventana)
    ventana.title(f"Vendedor - {nombre_usuario}")
    ventana.geometry("1400x900")
    ventana.after(0, lambda: ventana.state('zoomed') if os.name == 'nt' else None)

    # ========== HEADER ==========
    frame_header = ctk.CTkFrame(ventana, fg_color="#1e293b", height=70)
    frame_header.pack(fill="x")
    frame_header.pack_propagate(False)
    
    ctk.CTkLabel(
        frame_header, 
        text=f"💰 Vendedor: {nombre_usuario}", 
        font=("Roboto", 20, "bold"), 
        text_color="#facc15"
    ).pack(side="left", padx=25, pady=15)

    # ========== BODY (dos columnas) ==========
    frame_body = ctk.CTkFrame(ventana, fg_color="#0f172a")
    frame_body.pack(fill="both", expand=True)

    # ========== COLUMNA DERECHA: CARRITO ==========
    frame_carrito = ctk.CTkFrame(frame_body, fg_color="#1e293b", width=350)
    frame_carrito.pack(side="right", fill="y", padx=10, pady=10)
    frame_carrito.pack_propagate(False)

    ctk.CTkLabel(
        frame_carrito, 
        text="🛒 Carrito", 
        font=("Roboto", 16, "bold"), 
        text_color="#facc15"
    ).pack(pady=(15, 10))
    
    frame_lista = ctk.CTkScrollableFrame(frame_carrito, fg_color="#0f172a")
    frame_lista.pack(fill="both", expand=True, padx=10, pady=5)
    
    lbl_total = ctk.CTkLabel(
        frame_carrito, 
        text="Total: $0.00", 
        font=("Roboto", 16, "bold"), 
        text_color=COLOR_EXITO
    )
    lbl_total.pack(pady=10)

    carrito = {}  # {id_medicamento: {nombre, precio, cantidad, receta}}

    def actualizar_carrito_ui():
        """
        Actualiza la visualización del carrito.
        
        Redibuja todos los items con:
        - Nombre del medicamento
        - Precio unitario x cantidad = subtotal
        - Botones para ajustar cantidad
        - Total general
        """
        # Limpiar frame
        for w in frame_lista.winfo_children(): 
            w.destroy()
        
        # Calcular total
        total = sum(item["precio"] * item["cantidad"] for item in carrito.values())
        
        # Dibujar cada item
        for id_m, item in carrito.items():
            subtotal = item["precio"] * item["cantidad"]
            
            # Card para cada producto
            fr = ctk.CTkFrame(frame_lista, fg_color="#2d3748", corner_radius=10)
            fr.pack(fill="x", pady=5, padx=5)
            
            # Nombre del producto
            ctk.CTkLabel(
                fr, 
                text=item["nombre"], 
                font=("Roboto", 11, "bold"), 
                text_color="white", 
                wraplength=250
            ).pack(padx=8, pady=(8, 2), anchor="w")
            
            # Precio, cantidad y subtotal
            ctk.CTkLabel(
                fr, 
                text=f"${item['precio']:.2f} x{item['cantidad']} = ${subtotal:.2f}", 
                font=("Roboto", 10), 
                text_color="#9ca3af"
            ).pack(padx=8, pady=2)
            
            # Botones de control
            btn = ctk.CTkFrame(fr, fg_color="transparent")
            btn.pack(fill="x", padx=8, pady=(0, 8))
            
            def quitar(mid=id_m):
                """Reduce cantidad en 1 o elimina si es la última"""
                if carrito[mid]["cantidad"] > 1: 
                    carrito[mid]["cantidad"] -= 1
                else: 
                    del carrito[mid]
                actualizar_carrito_ui()

            ctk.CTkButton(
                btn, 
                text="-", 
                width=35, 
                height=28, 
                fg_color=COLOR_PELIGRO, 
                command=quitar
            ).pack(side="left", padx=2)
            
            ctk.CTkButton(
                btn, 
                text="✕", 
                width=35, 
                height=28, 
                fg_color="#64748b", 
                command=lambda mid=id_m: (carrito.pop(mid, None), actualizar_carrito_ui())
            ).pack(side="right", padx=2)
        
        # Actualizar total
        lbl_total.configure(text=f"Total: ${total:.2f}")

    def agregar(id_med, nombre, precio, requiere_receta, stock_disp):
        """
        Agrega medicamento al carrito con validaciones.
        
        Proceso:
        1. Valida que hay stock disponible
        2. Si requiere receta: solicita datos al usuario
        3. Agrega o incrementa cantidad en carrito
        4. Recarga visualización
        
        Args:
            id_med (str): ID del medicamento
            nombre (str): Nombre del medicamento
            precio (float): Precio unitario
            requiere_receta (bool): Si necesita prescripción
            stock_disp (int): Stock disponible
        """
        try:
            precio_float = float(precio)
            stock_int = int(stock_disp)
            
            # Cantidad actual en carrito
            cant_en_carrito = carrito.get(id_med, {}).get("cantidad", 0)
            
            # Validar stock
            if cant_en_carrito + 1 > stock_int:
                return messagebox.showwarning(
                    "Sin Stock", 
                    f"Stock insuficiente. Solo quedan {stock_int} unidades."
                )
            
            # Si requiere receta y es la primera vez que se agrega
            if requiere_receta and id_med not in carrito:
                dialog = ctk.CTkInputDialog(
                    text=f"El medicamento {nombre} requiere receta médica.\n\nIngrese Nombre del Doctor o N° de Receta:", 
                    title="Receta Requerida"
                )
                receta = dialog.get_input()
                
                if not receta or not receta.strip():
                    return messagebox.showwarning(
                        "Cancelado", 
                        "Es obligatorio ingresar los datos de la receta para continuar."
                    )
                
                # Agregar con receta
                if id_med not in carrito:
                    carrito[id_med] = {
                        "nombre": nombre, 
                        "precio": precio_float, 
                        "cantidad": 1, 
                        "receta": receta.strip()
                    }
                else:
                    carrito[id_med]["cantidad"] += 1
            else:
                # Medicamento sin receta o ya está en carrito
                if id_med in carrito: 
                    carrito[id_med]["cantidad"] += 1
                else: 
                    carrito[id_med] = {
                        "nombre": nombre, 
                        "precio": precio_float, 
                        "cantidad": 1, 
                        "receta": ""
                    }
            
            actualizar_carrito_ui()
        except (ValueError, TypeError) as e:
            messagebox.showerror(
                "❌ Error", 
                f"Error al agregar medicamento: {str(e)}"
            )

    # ========== COLUMNA IZQUIERDA: CATÁLOGO ==========
    frame_catalogo = ctk.CTkFrame(frame_body, fg_color="#0f172a")
    frame_catalogo.pack(side="left", fill="both", expand=True, padx=10, pady=10)

    # Barra de búsqueda y filtros
    frame_busqueda = ctk.CTkFrame(frame_catalogo, fg_color="#1e293b", corner_radius=10)
    frame_busqueda.pack(fill="x", pady=10)
    
    entry_buscar = ctk.CTkEntry(
        frame_busqueda, 
        placeholder_text="🔍 Buscar...", 
        width=300
    )
    entry_buscar.pack(side="left", padx=15, pady=10)

    combo_filtro = ctk.CTkComboBox(
        frame_busqueda, 
        values=["Todos", "Con Stock", "Sin Receta"]
    )
    combo_filtro.pack(side="left", padx=10, pady=10)
    combo_filtro.set("Todos")

    # Grid de medicamentos (4 columnas)
    frame_grid = ctk.CTkScrollableFrame(frame_catalogo, fg_color="#0f172a")
    frame_grid.pack(fill="both", expand=True)

    def mostrar_catalogo(*args):
        """
        Recarga el catálogo de medicamentos con filtros.
        
        Proceso:
        1. Limpia grid
        2. Obtiene término de búsqueda
        3. Busca medicamentos (o todos si vacío)
        4. Aplica filtros seleccionados
        5. Dibuja cards 4x4 con botones de agregar
        
        Cards visuales muestran:
        - Nombre del medicamento
        - Stock y marca
        - Indicador de receta requerida (⚠️)
        - Precio
        - Botón de agregar (deshabilitado si sin stock)
        """
        # Limpiar
        for w in frame_grid.winfo_children(): 
            w.destroy()
        
        termino = entry_buscar.get().strip()
        filtro = combo_filtro.get()
        
        try:
            # Obtener medicamentos
            if termino: 
                medicamentos = servicio_meds.buscar_medicamentos(nombre=termino)
            else: 
                medicamentos = repo_meds.obtener_todos()

            # Aplicar filtros
            if filtro == "Con Stock": 
                medicamentos = [m for m in medicamentos if m.stock > 0]
            elif filtro == "Sin Receta": 
                medicamentos = [m for m in medicamentos if not m.requiere_receta]

            # Dibujar cards en grid 4 columnas
            for idx, med in enumerate(medicamentos):
                fila, col = idx // 4, idx % 4
                
                # Color del borde (rojo si sin stock)
                color_borde = "#ef4444" if med.stock == 0 else "#334155"
                
                # Card del medicamento
                card = ctk.CTkFrame(
                    frame_grid, 
                    fg_color="#1e293b", 
                    corner_radius=12, 
                    border_width=2, 
                    border_color=color_borde
                )
                card.grid(row=fila, column=col, padx=10, pady=10)

                # Nombre
                ctk.CTkLabel(
                    card, 
                    text=med.nombre, 
                    font=("Roboto", 12, "bold"), 
                    text_color="white", 
                    wraplength=160
                ).pack(padx=10, pady=(10, 2))
                
                # Stock y marca
                ctk.CTkLabel(
                    card, 
                    text=f"Stock: {med.stock}  |  {med.marca}", 
                    font=("Roboto", 10), 
                    text_color="#9ca3af"
                ).pack()
                
                # Indicador de receta
                if med.requiere_receta:
                    ctk.CTkLabel(
                        card, 
                        text="⚠️ Requiere Receta", 
                        font=("Roboto", 10, "bold"), 
                        text_color=COLOR_ADVERTENCIA
                    ).pack()
                
                # Precio
                ctk.CTkLabel(
                    card, 
                    text=f"${med.precio_individual:.2f}", 
                    font=("Roboto", 14, "bold"), 
                    text_color=COLOR_EXITO
                ).pack(pady=5)

                # Botón de agregar
                btn = ctk.CTkButton(
                    card, 
                    text="➕ Agregar" if med.stock > 0 else "Agotado", 
                    fg_color=COLOR_BOTON if med.stock > 0 else "#475569", 
                    state="normal" if med.stock > 0 else "disabled",
                    command=lambda m=med: agregar(
                        m.id_medicamento, 
                        m.nombre, 
                        m.precio_individual, 
                        m.requiere_receta, 
                        m.stock
                    )
                )
                btn.pack(fill="x", padx=10, pady=(0, 10))
        
        except ValueError as e:
            messagebox.showwarning("Búsqueda", str(e))
            # Limpiar búsqueda y reintentar
            entry_buscar.delete(0, 'end')
            mostrar_catalogo()

    # Conectar eventos de búsqueda
    entry_buscar.bind("<KeyRelease>", mostrar_catalogo)
    combo_filtro.configure(command=mostrar_catalogo)
    
    # Cargar catálogo inicial
    mostrar_catalogo()

    def cobrar():
        """
        Procesa la venta: registra transacciones y genera recibo.
        
        Proceso:
        1. Valida que carrito no esté vacío
        2. Registra cada medicamento como venta separada
        3. Persiste cambios de stock automáticamente
        4. Genera archivo de recibo en carpeta 'tickets'
        5. Muestra confirmación al usuario
        6. Limpia carrito y recarga catálogo
        
        El recibo incluye:
        - Encabezado de farmacia
        - Fecha y hora
        - Nombre del cajero
        - Detalle de productos (nombre, cantidad, subtotal)
        - Total a pagar
        """
        if not carrito: 
            return messagebox.showwarning(
                "Carrito Vacío", 
                "Agrega medicamentos al carrito primero."
            )
        
        total = sum(item["precio"] * item["cantidad"] for item in carrito.values())
        
        try:
            # Registrar cada medicamento como venta
            for id_med, item in carrito.items():
                receta = item.get("receta", "")
                servicio_ventas.registrar_venta(
                    id_med, 
                    item["cantidad"], 
                    nombre_usuario, 
                    receta
                )
            
            # Generar recibo en archivo de texto
            ruta_directorio_tickets = os.path.join(os.path.dirname(__file__), "tickets")
            if not os.path.exists(ruta_directorio_tickets): 
                os.makedirs(ruta_directorio_tickets)
            
            fecha_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            ruta_ticket = os.path.join(ruta_directorio_tickets, f"ticket_{fecha_str}.txt")
            
            with open(ruta_ticket, "w", encoding="utf-8") as f:
                f.write("="*40 + "\n         FARMACIA DR CLARA\n" + "="*40 + "\n")
                f.write(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Cajero: {nombre_usuario}\n")
                f.write("-" * 40 + "\n")
                f.write(f"{'Producto':<20} {'Cant':<5} {'Subtotal':<10}\n")
                
                for item in carrito.values():
                    f.write(
                        f"{item['nombre'][:19]:<20} "
                        f"{item['cantidad']:<5} "
                        f"${item['precio']*item['cantidad']:.2f}\n"
                    )
                
                f.write("-" * 40 + "\n")
                f.write(f"TOTAL A PAGAR: ${total:.2f}\n")
                f.write("="*40 + "\n")
                f.write("      ¡Gracias por su compra!\n")

            messagebox.showinfo(
                "✓ Venta Exitosa", 
                f"Venta registrada correctamente.\n"
                f"Total: ${total:.2f}\n\n"
                f"Recibo generado en la carpeta 'tickets'"
            )
            
            # Limpiar carrito
            carrito.clear()
            actualizar_carrito_ui()
            
            # Recargar catálogo (actualiza stock)
            mostrar_catalogo()
        
        except ValueError as e:
            messagebox.showerror("❌ Error", str(e))
        except Exception as e:
            messagebox.showerror(
                "❌ Error Inesperado", 
                f"Error al procesar la venta: {str(e)}"
            )

    # Botón de cobro
    ctk.CTkButton(
        frame_carrito, 
        text="💳 COBRAR E IMPRIMIR", 
        width=300, 
        height=60, 
        fg_color=COLOR_EXITO, 
        font=("Roboto", 16, "bold"), 
        command=cobrar
    ).pack(pady=10)
    
    # Botón de cierre de sesión
    ctk.CTkButton(
        ventana, 
        text="Cerrar Sesión", 
        fg_color=COLOR_PELIGRO, 
        font=("Roboto", 14, "bold"), 
        command=lambda: mostrar_pantalla_login(ventana)
    ).pack(pady=15)


# ============================================================
# PANTALLA 4: GERENTE (Reportes y Análisis)
# ============================================================

def mostrar_pantalla_gerente(ventana, nombre_usuario):
    """
    Interfaz de administrador para gerentes: reportes y análisis.
    
    Funcionalidades:
    - Resumen de últimos 7 días
    - Total de ventas y ganancias
    - Tabla detallada de ventas por producto
    - Gráfico de barras con Top 5 productos
    - Tabla de últimas 15 transacciones con información de recetas
    
    Los datos mostrados son de los últimos 7 días para análisis semanal.
    
    Args:
        ventana (CTkFrame): Ventana principal
        nombre_usuario (str): Nombre del gerente logueado
    """
    limpiar_pantalla(ventana)
    ventana.title(f"Gerente - {nombre_usuario}")
    ventana.geometry("1400x900")
    ventana.after(0, lambda: ventana.state('zoomed') if os.name == 'nt' else None)

    # ========== HEADER ==========
    frame_header = ctk.CTkFrame(ventana, fg_color="#1e293b", height=70)
    frame_header.pack(fill="x")
    frame_header.pack_propagate(False)
    
    ctk.CTkLabel(
        frame_header, 
        text=f"📊 Gerente: {nombre_usuario}", 
        font=("Roboto", 20, "bold"), 
        text_color="#8b5cf6"
    ).pack(side="left", padx=25, pady=15)

    # ========== BODY ==========
    frame_body = ctk.CTkFrame(ventana, fg_color="#0f172a")
    frame_body.pack(fill="both", expand=True, padx=20, pady=20)

    # ========== ESTADÍSTICAS SEMANALES ==========
    try:
        stats = servicio_ventas.obtener_estadisticas_semanales()

        frame_stats = ctk.CTkFrame(frame_body, fg_color="#1e293b", corner_radius=12)
        frame_stats.pack(fill="x", pady=10)
        
        ctk.CTkLabel(
            frame_stats, 
            text="📈 Resumen Últimos 7 Días", 
            font=("Roboto", 16, "bold"), 
            text_color="#facc15"
        ).pack(pady=(15, 5))
        
        stats_info = ctk.CTkFrame(frame_stats, fg_color="transparent")
        stats_info.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkLabel(
            stats_info, 
            text=f"📌 Total de Ventas: {stats['total_ventas']}", 
            font=("Roboto", 14, "bold"), 
            text_color=COLOR_EXITO
        ).pack(side="left", padx=20)
        
        ctk.CTkLabel(
            stats_info, 
            text=f"💰 Ganancias Totales: ${stats['total_ganancias']:.2f}", 
            font=("Roboto", 14, "bold"), 
            text_color=COLOR_EXITO
        ).pack(side="left", padx=20)

        # ========== GRÁFICO Y TABLA DE PRODUCTOS ==========
        frame_graf_tab = ctk.CTkFrame(frame_body, fg_color="transparent")
        frame_graf_tab.pack(fill="both", expand=True)

        # Tabla de medicamentos más vendidos
        frame_medicamentos = ctk.CTkFrame(frame_graf_tab, fg_color="#1e293b", corner_radius=12)
        frame_medicamentos.pack(side="left", fill="both", expand=True, padx=(0, 10))

        ctk.CTkLabel(
            frame_medicamentos, 
            text="💊 Detalle de Ventas por Producto", 
            font=("Roboto", 14, "bold"), 
            text_color="#facc15"
        ).pack(pady=(15, 10))

        cols_meds = ("Medicamento", "Vendidos", "Ganancia")
        tabla_meds = ttk.Treeview(frame_medicamentos, columns=cols_meds, show="headings", height=8)
        
        for col in cols_meds: 
            tabla_meds.heading(col, text=col)
        
        tabla_meds.column("Medicamento", width=250)
        tabla_meds.column("Vendidos", width=100)
        tabla_meds.column("Ganancia", width=150)
        
        tabla_meds.pack(fill="both", expand=True, padx=15, pady=10)

        # Llenar tabla con estadísticas
        for med_id, datos in stats['medicamentos_vendidos'].items():
            tabla_meds.insert(
                "", "end", 
                values=(
                    datos['nombre'], 
                    datos['cantidad'], 
                    f"${datos['ganancia']:.2f}"
                )
            )

        # Gráfico de barras Top 5
        frame_grafico = ctk.CTkFrame(frame_graf_tab, fg_color="#1e293b", corner_radius=12)
        frame_grafico.pack(side="right", fill="both", expand=True, padx=(10, 0))
        
        ctk.CTkLabel(
            frame_grafico, 
            text="📊 Top 5 Productos (Ingresos)", 
            font=("Roboto", 14, "bold"), 
            text_color="#3b82f6"
        ).pack(pady=(15, 10))

        canvas = ctk.CTkCanvas(frame_grafico, bg="#1e293b", highlightthickness=0)
        canvas.pack(fill="both", expand=True, padx=20, pady=10)

        # Obtener top 5
        top_meds = sorted(
            stats['medicamentos_vendidos'].values(), 
            key=lambda x: x['ganancia'], 
            reverse=True
        )[:5]
        
        if top_meds:
            max_ganancia = top_meds[0]['ganancia']
            
            def draw_chart(event=None):
                """
                Dibuja gráfico de barras con Top 5 productos.
                
                Características:
                - Barras azules proporcionales a ganancias
                - Nombre del producto en eje X
                - Valor en dinero en eje Y
                - Se actualiza al redimensionar ventana
                """
                canvas.delete("all")
                w, h = canvas.winfo_width(), canvas.winfo_height()
                
                # Validar tamaño mínimo
                if w < 50 or h < 50: 
                    return
                
                bar_width = w / (len(top_meds) * 2)
                spacing = bar_width
                x_offset = spacing / 2
                
                # Dibujar cada barra
                for med in top_meds:
                    # Altura proporcional a ganancia
                    bar_height = (med['ganancia'] / max_ganancia) * (h - 60) if max_ganancia > 0 else 0
                    x0, y0 = x_offset, h - 30 - bar_height
                    x1, y1 = x0 + bar_width, h - 30
                    
                    # Rectángulo (barra)
                    canvas.create_rectangle(x0, y0, x1, y1, fill="#3b82f6", outline="")
                    
                    # Nombre del producto (X)
                    canvas.create_text(
                        x0 + bar_width/2, 
                        y1 + 15, 
                        text=med['nombre'][:12], 
                        fill="white", 
                        font=("Roboto", 9)
                    )
                    
                    # Valor en dinero (Y)
                    canvas.create_text(
                        x0 + bar_width/2, 
                        y0 - 10, 
                        text=f"${med['ganancia']:.0f}", 
                        fill="#facc15", 
                        font=("Roboto", 10, "bold")
                    )
                    
                    x_offset += bar_width + spacing
            
            # Redibujar cuando cambia tamaño
            canvas.bind("<Configure>", draw_chart)

        # ========== HISTORIAL DE ÚLTIMAS VENTAS ==========
        frame_ventas = ctk.CTkFrame(frame_body, fg_color="#1e293b", corner_radius=12)
        frame_ventas.pack(fill="x", pady=10)

        ctk.CTkLabel(
            frame_ventas, 
            text="🧾 Últimas Ventas", 
            font=("Roboto", 14, "bold"), 
            text_color="#facc15"
        ).pack(pady=(10, 5))
        
        cols = ("ID", "Medicamento", "Cant", "Total", "Empleado", "Fecha", "Receta")
        tabla = ttk.Treeview(frame_ventas, columns=cols, show="headings", height=8)
        
        for col in cols: 
            tabla.heading(col, text=col)
        
        tabla.column("ID", width=60)
        tabla.column("Medicamento", width=200)
        tabla.column("Cant", width=60)
        tabla.column("Total", width=80)
        tabla.column("Empleado", width=100)
        tabla.column("Fecha", width=150)
        tabla.column("Receta", width=100)
        
        tabla.pack(fill="both", expand=True, padx=15, pady=10)

        # Llenar tabla con últimas 15 ventas
        for v in reversed(repo_ventas.obtener_todos()[-15:]):
            tabla.insert(
                "", "end", 
                values=(
                    v.id_venta, 
                    v.nombre_medicamento, 
                    v.cantidad_vendida, 
                    f"${v.precio_total:.2f}", 
                    v.empleado, 
                    v.fecha_hora, 
                    v.receta if v.receta else "—"
                )
            )
    
    except Exception as e:
        messagebox.showerror("❌ Error", f"Error al cargar datos: {str(e)}")

    # Botón de cierre de sesión
    ctk.CTkButton(
        ventana, 
        text="Cerrar Sesión", 
        fg_color=COLOR_PELIGRO, 
        font=("Roboto", 14, "bold"), 
        command=lambda: mostrar_pantalla_login(ventana)
    ).pack(pady=15)


# ============================================================
# FUNCIÓN PRINCIPAL Y PUNTO DE ENTRADA
# ============================================================

def iniciar_aplicacion():
    """
    Inicializa y ejecuta la aplicación.
    
    Proceso:
    1. Crea ventana principal de CustomTkinter
    2. Configura dimensiones y color de fondo
    3. Muestra pantalla de login
    4. Inicia el event loop de la interfaz
    """
    ventana = ctk.CTk()
    ventana.geometry("600x600")
    ventana.configure(fg_color=COLOR_FONDO)
    ventana.title("Farmacia Dr Clara")
    
    # Mostrar pantalla inicial (login)
    mostrar_pantalla_login(ventana)
    
    # Iniciar la aplicación
    ventana.mainloop()


# ============================================================
# PUNTO DE ENTRADA DEL PROGRAMA
# ============================================================

if __name__ == "__main__":
    """
    Script principal: ejecuta la aplicación cuando se corre directamente.
    
    Uso:
        python frontend.py
    """
    iniciar_aplicacion()
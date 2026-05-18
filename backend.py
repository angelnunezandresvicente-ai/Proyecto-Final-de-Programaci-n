"""
SISTEMA DE GESTIÓN DE FARMACIA - BACKEND
==========================================
Módulo principal que contiene toda la lógica de negocio para la gestión
de medicamentos, ventas, usuarios y almacenamiento en CSV.

Características principales:
- Gestión de inventario de medicamentos
- Control de ventas y reportes
- Autenticación de usuarios con protección contra fuerza bruta
- Persistencia de datos en archivos CSV
- Validaciones exhaustivas de datos
- Sistema de caché para búsquedas optimizadas
"""

import csv
import os
from datetime import datetime, timedelta
from abc import ABC, abstractmethod
import uuid
import shutil
import tempfile

# ============================================================
# MODELOS DE DOMINIO
# ============================================================

class Medicamento:
    """
    Representa un medicamento en el inventario de la farmacia.
    
    Atributos:
        id_medicamento (str): Identificador único del medicamento (formato: M_TIMESTAMP_RANDOM)
        nombre (str): Nombre del medicamento
        precio (float): Precio total/mayorista del medicamento
        cantidad (str): Presentación del medicamento (ej: 500ml, 100 caps)
        fecha_caducidad (str): Fecha de vencimiento en formato YYYY-MM-DD
        marca (str): Marca fabricante del medicamento
        precio_individual (float): Precio unitario de venta al cliente
        stock (int): Cantidad disponible en inventario
        requiere_receta (bool): Indica si necesita prescripción médica
    """
    
    def __init__(self, id_med, nombre, precio, cantidad, fecha_caducidad, marca, 
                 precio_individual=0.0, stock=0, requiere_receta=False):
        self.id_medicamento = id_med
        self.nombre = nombre
        self.precio = float(precio)
        self.cantidad = cantidad  # Presentación (no cantidad de stock)
        self.fecha_caducidad = fecha_caducidad
        self.marca = marca
        self.precio_individual = float(precio_individual) if precio_individual else self.precio
        self.stock = int(stock)
        self.requiere_receta = str(requiere_receta).lower() == 'true'


class Venta:
    """
    Representa una transacción de venta realizada en la farmacia.
    
    Atributos:
        id_venta (str): Identificador único de la venta (formato: V_NUMERO)
        medicamento_id (str): ID del medicamento vendido
        nombre_medicamento (str): Nombre del medicamento (para registro rápido)
        cantidad_vendida (int): Cantidad de unidades vendidas
        precio_unitario (float): Precio por unidad al momento de la venta
        precio_total (float): Total de la transacción (cantidad * precio_unitario)
        fecha_hora (str): Timestamp de la venta (YYYY-MM-DD HH:MM:SS)
        empleado (str): Nombre del vendedor que realizó la transacción
        receta (str): Datos de la receta médica (si aplica)
    """
    
    def __init__(self, id_venta, medicamento_id, nombre_medicamento, cantidad_vendida, 
                 precio_unitario, precio_total, fecha_hora, empleado, receta=""):
        self.id_venta = id_venta
        self.medicamento_id = medicamento_id
        self.nombre_medicamento = nombre_medicamento
        self.cantidad_vendida = int(cantidad_vendida)
        self.precio_unitario = float(precio_unitario)
        self.precio_total = float(precio_total)
        self.fecha_hora = fecha_hora
        self.empleado = empleado
        self.receta = receta  # Campo agregado para guardar datos de receta


class Usuario:
    """
    Representa un empleado/usuario del sistema farmacéutico.
    
    Atributos:
        nombre (str): Identificador único del usuario
        rol (str): Rol del usuario ('gerente', 'farmaceuta' o 'vendedor')
        password (str): Contraseña del usuario (almacenada en texto plano por simplicidad)
    """
    
    def __init__(self, nombre, rol, password):
        self.nombre = nombre
        self.rol = rol
        self.password = password


# ============================================================
# PATRÓN REPOSITORY (Acceso a datos)
# ============================================================

class Repository(ABC):
    """
    Clase abstracta que define la interfaz para acceder a datos.
    
    Implementa el patrón Repository para abstraer la lógica de persistencia.
    Todos los repositorios deben implementar estos métodos.
    """
    
    @abstractmethod
    def guardar(self, entidad):
        """Guarda una nueva entidad en el repositorio"""
        pass
    
    @abstractmethod
    def obtener_por_id(self, id_entidad):
        """Obtiene una entidad por su ID"""
        pass
    
    @abstractmethod
    def obtener_todos(self):
        """Obtiene todas las entidades del repositorio"""
        pass
    
    @abstractmethod
    def actualizar(self, entidad):
        """Actualiza una entidad existente"""
        pass
    
    @abstractmethod
    def eliminar(self, id_entidad):
        """Elimina una entidad por su ID"""
        pass


class RepositorioUsuariosCSV(Repository):
    """
    Repositorio para gestionar usuarios persistidos en archivo CSV.
    
    Responsabilidades:
    - Cargar usuarios desde usuarios.csv
    - Mantener usuarios en memoria en un diccionario
    - Persistir cambios en el archivo CSV
    - Crear backups automáticos antes de sobrescribir
    - Manejar errores de permisos de archivo
    """
    
    def __init__(self, archivo="usuarios.csv"):
        """
        Inicializa el repositorio y carga los usuarios existentes.
        
        Args:
            archivo (str): Nombre del archivo CSV (default: usuarios.csv)
        """
        self.archivo = os.path.join(os.path.dirname(__file__), archivo)
        self.usuarios = {}  # Diccionario {nombre: Usuario}
        self._cargar()
    
    def _cargar(self):
        """
        Carga los usuarios desde el archivo CSV a memoria.
        
        Si el archivo no existe, muestra advertencia pero continúa.
        Si hay error de lectura, lo registra pero no falla.
        """
        if not os.path.exists(self.archivo): 
            print(f"[ADVERTENCIA] Archivo {self.archivo} no existe")
            return
        try:
            with open(self.archivo, mode='r', newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    usuario = Usuario(
                        row["nombre"].strip(), 
                        row["rol"].strip(), 
                        row["password"].strip()
                    )
                    self.usuarios[usuario.nombre] = usuario
            print(f"[INFO] {len(self.usuarios)} usuarios cargados")
        except Exception as e:
            print(f"[ERROR] No se pudo cargar usuarios.csv: {e}")
    
    def guardar(self, usuario):
        """
        Guarda un nuevo usuario en memoria y persiste en CSV.
        
        Args:
            usuario (Usuario): Objeto usuario a guardar
            
        Raises:
            ValueError: Si el usuario ya existe
        """
        if usuario.nombre in self.usuarios: 
            raise ValueError("Usuario ya existe.")
        self.usuarios[usuario.nombre] = usuario
        self._persistir()
    
    def obtener_por_id(self, nombre):
        """
        Obtiene un usuario por su nombre (identificador único).
        
        Args:
            nombre (str): Nombre del usuario
            
        Returns:
            Usuario: Objeto usuario o None si no existe
        """
        return self.usuarios.get(nombre.strip() if nombre else "")
    
    def obtener_todos(self):
        """
        Obtiene todos los usuarios registrados.
        
        Returns:
            list: Lista de todos los objetos Usuario
        """
        return list(self.usuarios.values())
    
    def actualizar(self, usuario):
        """
        Actualiza un usuario existente.
        
        Args:
            usuario (Usuario): Usuario con datos actualizados
            
        Raises:
            ValueError: Si el usuario no existe
        """
        if usuario.nombre not in self.usuarios: 
            raise ValueError("Usuario no existe.")
        self.usuarios[usuario.nombre] = usuario
        self._persistir()
    
    def eliminar(self, nombre):
        """
        Elimina un usuario del sistema.
        
        Args:
            nombre (str): Nombre del usuario a eliminar
            
        Raises:
            ValueError: Si el usuario no existe
        """
        if nombre not in self.usuarios: 
            raise ValueError("Usuario no existe.")
        del self.usuarios[nombre]
        self._persistir()
    
    def _persistir(self):
        """
        Persiste todos los usuarios en el archivo CSV con manejo seguro.
        
        Implementa un proceso seguro:
        1. Escribe en un archivo temporal
        2. Crea backup del archivo original
        3. Reemplaza el original con el temporal
        4. Maneja errores de permisos y otros excepciones
        """
        try:
            with tempfile.NamedTemporaryFile(mode='w', newline='', encoding='utf-8', 
                                            delete=False, dir=os.path.dirname(self.archivo)) as tmp:
                writer = csv.DictWriter(tmp, fieldnames=["nombre", "rol", "password"])
                writer.writeheader()
                for u in self.usuarios.values():
                    writer.writerow({
                        "nombre": u.nombre, 
                        "rol": u.rol, 
                        "password": u.password
                    })
                tmp_path = tmp.name
            
            # Crear backup del archivo original
            if os.path.exists(self.archivo):
                shutil.copy2(self.archivo, self.archivo + '.bak')
            
            # Reemplazar archivo original con temporal
            shutil.move(tmp_path, self.archivo)
            print(f"[INFO] usuarios.csv guardado correctamente")
        
        except PermissionError:
            # Error de permisos: archivo abierto en otro programa
            if 'tmp_path' in locals() and os.path.exists(tmp_path):
                os.remove(tmp_path)
            raise ValueError("Error de permisos: Asegúrate de que usuarios.csv no esté abierto en Excel u otro programa.")
        except Exception as e:
            print(f"[ERROR] No se pudo guardar usuarios.csv: {e}")
            if 'tmp_path' in locals() and os.path.exists(tmp_path):
                os.remove(tmp_path)
            raise


class RepositorioMedicamentosCSV(Repository):
    """
    Repositorio para gestionar medicamentos persistidos en archivo CSV.
    
    Responsabilidades:
    - Cargar medicamentos desde medicamentos.csv
    - Mantener medicamentos en memoria con caché opcional
    - Persistir cambios de stock automáticamente
    - Validar integridad de datos (fechas, precios)
    - Implementar búsquedas por nombre y marca
    - Detectar medicamentos próximos a caducar
    """
    
    def __init__(self, archivo="medicamentos.csv"):
        """
        Inicializa el repositorio de medicamentos.
        
        Args:
            archivo (str): Nombre del archivo CSV (default: medicamentos.csv)
        """
        self.archivo = os.path.join(os.path.dirname(__file__), archivo)
        self.medicamentos = {}  # Diccionario {id_medicamento: Medicamento}
        self._cargar()
    
    def _cargar(self):
        """
        Carga todos los medicamentos desde el archivo CSV a memoria.
        
        Maneja valores faltantes:
        - precio_individual: usa precio si no existe
        - stock: default 100
        - requiere_receta: default False
        
        Esto garantiza compatibilidad con versiones antiguas del CSV.
        """
        if not os.path.exists(self.archivo): 
            print(f"[ADVERTENCIA] Archivo {self.archivo} no existe")
            return
        try:
            with open(self.archivo, mode='r', newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    med = Medicamento(
                        id_med=row["id_medicamento"].strip(),
                        nombre=row["nombre"].strip(),
                        precio=float(row["precio"]),
                        cantidad=row["cantidad"].strip(),
                        fecha_caducidad=row["fecha_caducidad"].strip(),
                        marca=row["marca"].strip(),
                        precio_individual=float(row.get("precio_individual", row["precio"])),
                        stock=int(row.get("stock", 100)),  # Stock por defecto
                        requiere_receta=row.get("requiere_receta", "False")
                    )
                    self.medicamentos[med.id_medicamento] = med
            print(f"[INFO] {len(self.medicamentos)} medicamentos cargados")
        except Exception as e:
            print(f"[ERROR] No se pudo cargar medicamentos.csv: {e}")
    
    def guardar(self, medicamento):
        """
        Guarda un nuevo medicamento.
        
        Args:
            medicamento (Medicamento): Medicamento a guardar
            
        Raises:
            ValueError: Si el medicamento ya existe
        """
        if medicamento.id_medicamento in self.medicamentos: 
            raise ValueError("Ya existe.")
        self.medicamentos[medicamento.id_medicamento] = medicamento
        self._persistir()
    
    def obtener_por_id(self, id_medicamento):
        """
        Obtiene un medicamento por su ID.
        
        Args:
            id_medicamento (str): ID del medicamento
            
        Returns:
            Medicamento: Objeto medicamento o None
        """
        return self.medicamentos.get(id_medicamento)
    
    def obtener_todos(self):
        """
        Obtiene todos los medicamentos.
        
        Returns:
            list: Lista de todos los medicamentos
        """
        return list(self.medicamentos.values())
    
    def actualizar(self, medicamento):
        """
        Actualiza un medicamento existente (principalmente para cambios de stock).
        
        Args:
            medicamento (Medicamento): Medicamento con datos actualizados
            
        Raises:
            ValueError: Si el medicamento no existe
        """
        if medicamento.id_medicamento not in self.medicamentos: 
            raise ValueError("No existe.")
        self.medicamentos[medicamento.id_medicamento] = medicamento
        self._persistir()
    
    def eliminar(self, id_medicamento):
        """
        Elimina un medicamento del inventario.
        
        Args:
            id_medicamento (str): ID del medicamento a eliminar
            
        Raises:
            ValueError: Si el medicamento no existe
        """
        if id_medicamento not in self.medicamentos: 
            raise ValueError("No existe.")
        del self.medicamentos[id_medicamento]
        self._persistir()
    
    def _persistir(self):
        """
        Persiste todos los medicamentos en el CSV de forma segura.
        
        Implementa:
        - Escritura en archivo temporal
        - Backup automático
        - Manejo robusto de errores
        - Preservación de datos ante fallos
        """
        try:
            with tempfile.NamedTemporaryFile(mode='w', newline='', encoding='utf-8', 
                                            delete=False, dir=os.path.dirname(self.archivo)) as tmp:
                writer = csv.DictWriter(tmp, fieldnames=[
                    "id_medicamento", "nombre", "precio", "cantidad",
                    "fecha_caducidad", "marca", "precio_individual",
                    "stock", "requiere_receta"
                ])
                writer.writeheader()
                for med in self.medicamentos.values():
                    writer.writerow({
                        "id_medicamento": med.id_medicamento,
                        "nombre": med.nombre,
                        "precio": med.precio,
                        "cantidad": med.cantidad,
                        "fecha_caducidad": med.fecha_caducidad,
                        "marca": med.marca,
                        "precio_individual": med.precio_individual,
                        "stock": med.stock,
                        "requiere_receta": str(med.requiere_receta)
                    })
                tmp_path = tmp.name
            
            if os.path.exists(self.archivo):
                shutil.copy2(self.archivo, self.archivo + '.bak')
            
            shutil.move(tmp_path, self.archivo)
            print(f"[INFO] medicamentos.csv guardado correctamente")
        
        except PermissionError:
            if 'tmp_path' in locals() and os.path.exists(tmp_path):
                os.remove(tmp_path)
            raise ValueError("Error de permisos: Asegúrate de que medicamentos.csv no esté abierto en Excel.")
        except Exception as e:
            print(f"[ERROR] No se pudo guardar medicamentos.csv: {e}")
            if 'tmp_path' in locals() and os.path.exists(tmp_path):
                os.remove(tmp_path)
            raise
    
    def buscar_por_nombre(self, nombre):
        """
        Busca medicamentos por nombre (búsqueda parcial).
        
        Args:
            nombre (str): Parte del nombre a buscar
            
        Returns:
            list: Lista de medicamentos que coinciden
            
        Raises:
            ValueError: Si la búsqueda tiene menos de 2 caracteres
        """
        nl = nombre.lower().strip()
        if len(nl) < 2:
            raise ValueError("La búsqueda debe tener al menos 2 caracteres")
        return [m for m in self.medicamentos.values() if nl in m.nombre.lower()]
    
    def buscar_por_marca(self, marca):
        """
        Busca medicamentos por marca (búsqueda parcial).
        
        Args:
            marca (str): Parte de la marca a buscar
            
        Returns:
            list: Lista de medicamentos que coinciden
            
        Raises:
            ValueError: Si la búsqueda tiene menos de 2 caracteres
        """
        ml = marca.lower().strip()
        if len(ml) < 2:
            raise ValueError("La búsqueda debe tener al menos 2 caracteres")
        return [m for m in self.medicamentos.values() if ml in m.marca.lower()]
    
    def existe_duplicado(self, nombre, marca, cantidad):
        """
        Verifica si existe un medicamento con los mismos datos.
        
        Se usa para evitar duplicados al registrar nuevos medicamentos.
        
        Args:
            nombre (str): Nombre del medicamento
            marca (str): Marca del medicamento
            cantidad (str): Presentación del medicamento
            
        Returns:
            bool: True si existe duplicado, False en caso contrario
        """
        return any(
            m.nombre.lower() == nombre.lower() and 
            m.marca.lower() == marca.lower() and 
            m.cantidad == cantidad 
            for m in self.medicamentos.values()
        )
    
    def obtener_proximos_a_caducar(self, dias=30):
        """
        Obtiene medicamentos que vencen en los próximos N días.
        
        Usado por farmacéuticos para alertas de expiración.
        Ignora medicamentos con fechas inválidas.
        
        Args:
            dias (int): Días a futuro para búsqueda (default: 30)
            
        Returns:
            list: Medicamentos próximos a caducar, ordenados por fecha
        """
        fecha_limite = datetime.now() + timedelta(days=dias)
        resultados = []
        for m in self.medicamentos.values():
            try:
                fecha_obj = datetime.strptime(m.fecha_caducidad, "%Y-%m-%d")
                if fecha_obj <= fecha_limite:
                    resultados.append(m)
            except ValueError:
                # Fecha mal formateada - se ignora silenciosamente
                print(f"[ADVERTENCIA] Fecha inválida en medicamento {m.id_medicamento}: {m.fecha_caducidad}")
        return resultados


class RepositorioVentasCSV(Repository):
    """
    Repositorio para gestionar el historial de ventas en CSV.
    
    Responsabilidades:
    - Registrar todas las transacciones de ventas
    - Mantener historial completo para auditoría
    - Generar reportes de ventas
    - Filtrar por período (últimos 7 días para estadísticas)
    - Guardar información de recetas médicas
    """
    
    def __init__(self, archivo="ventas.csv"):
        """
        Inicializa el repositorio de ventas.
        
        Args:
            archivo (str): Nombre del archivo CSV (default: ventas.csv)
        """
        self.archivo = os.path.join(os.path.dirname(__file__), archivo)
        self.ventas = []  # Lista de todas las ventas registradas
        self._cargar()
    
    def _cargar(self):
        """
        Carga todas las ventas históricas desde el CSV.
        
        Las ventas son de solo lectura después de registrarse.
        El campo receta es opcional para compatibilidad con datos antiguos.
        """
        if not os.path.exists(self.archivo): 
            print(f"[ADVERTENCIA] Archivo {self.archivo} no existe")
            return
        try:
            with open(self.archivo, mode='r', newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    venta = Venta(
                        row["id_venta"].strip(), 
                        row["medicamento_id"].strip(),
                        row["nombre_medicamento"].strip(), 
                        row["cantidad_vendida"],
                        row["precio_unitario"], 
                        row["precio_total"],
                        row["fecha_hora"].strip(), 
                        row["empleado"].strip(),
                        row.get("receta", "")  # Campo opcional
                    )
                    self.ventas.append(venta)
            print(f"[INFO] {len(self.ventas)} ventas cargadas")
        except Exception as e:
            print(f"[ERROR] No se pudo cargar ventas.csv: {e}")
    
    def guardar(self, venta):
        """
        Registra una nueva venta en el historial.
        
        Args:
            venta (Venta): Objeto venta a registrar
        """
        self.ventas.append(venta)
        self._persistir()
    
    def obtener_por_id(self, id_venta):
        """
        Obtiene una venta por su ID.
        
        Args:
            id_venta (str): ID de la venta
            
        Returns:
            Venta: Objeto venta o None
        """
        return next((v for v in self.ventas if v.id_venta == id_venta), None)
    
    def obtener_todos(self):
        """
        Obtiene todo el historial de ventas.
        
        Returns:
            list: Lista de todas las ventas registradas
        """
        return self.ventas
    
    def actualizar(self, venta):
        """
        Actualiza una venta existente (rara vez usado).
        
        Args:
            venta (Venta): Venta con datos actualizados
            
        Raises:
            ValueError: Si la venta no existe
        """
        venta_ex = self.obtener_por_id(venta.id_venta)
        if not venta_ex: 
            raise ValueError("No existe.")
        self.ventas[self.ventas.index(venta_ex)] = venta
        self._persistir()
    
    def eliminar(self, id_venta):
        """
        Elimina una venta del historial (para correcciones).
        
        Args:
            id_venta (str): ID de la venta a eliminar
        """
        v = self.obtener_por_id(id_venta)
        if v: 
            self.ventas.remove(v)
            self._persistir()
    
    def _persistir(self):
        """
        Persiste todas las ventas en el CSV con procedimiento seguro.
        
        Las ventas nunca se modifican, solo se agregan o eliminan.
        """
        try:
            with tempfile.NamedTemporaryFile(mode='w', newline='', encoding='utf-8', 
                                            delete=False, dir=os.path.dirname(self.archivo)) as tmp:
                writer = csv.DictWriter(tmp, fieldnames=[
                    "id_venta", "medicamento_id", "nombre_medicamento",
                    "cantidad_vendida", "precio_unitario", "precio_total",
                    "fecha_hora", "empleado", "receta"
                ])
                writer.writeheader()
                for v in self.ventas:
                    writer.writerow({
                        "id_venta": v.id_venta,
                        "medicamento_id": v.medicamento_id,
                        "nombre_medicamento": v.nombre_medicamento,
                        "cantidad_vendida": v.cantidad_vendida,
                        "precio_unitario": v.precio_unitario,
                        "precio_total": v.precio_total,
                        "fecha_hora": v.fecha_hora,
                        "empleado": v.empleado,
                        "receta": v.receta
                    })
                tmp_path = tmp.name
            
            if os.path.exists(self.archivo):
                shutil.copy2(self.archivo, self.archivo + '.bak')
            
            shutil.move(tmp_path, self.archivo)
            print(f"[INFO] ventas.csv guardado correctamente")
        
        except PermissionError:
            if 'tmp_path' in locals() and os.path.exists(tmp_path):
                os.remove(tmp_path)
            raise ValueError("Error de permisos: Asegúrate de que ventas.csv no esté abierto.")
        except Exception as e:
            print(f"[ERROR] No se pudo guardar ventas.csv: {e}")
            if 'tmp_path' in locals() and os.path.exists(tmp_path):
                os.remove(tmp_path)
            raise
    
    def obtener_estadisticas_semanales(self):
        """
        Calcula estadísticas de ventas para los últimos 7 días.
        
        Usado por gerentes para reportes y toma de decisiones.
        Solo incluye ventas de la última semana.
        
        Returns:
            dict: Diccionario con:
                - total_ventas: cantidad de transacciones
                - total_ganancias: suma de ingresos
                - medicamentos_vendidos: detalles por producto
        """
        meds = {}  # {medicamento_id: {nombre, cantidad, ganancia}}
        total_ventas = 0
        total_ganancias = 0.0
        hace_una_semana = datetime.now() - timedelta(days=7)

        for v in self.ventas:
            try:
                # Filtrar ventas por período (últimos 7 días)
                fecha_venta = datetime.strptime(v.fecha_hora, "%Y-%m-%d %H:%M:%S")
                if fecha_venta >= hace_una_semana:
                    total_ventas += 1
                    total_ganancias += v.precio_total

                    # Agregar a estadísticas de medicamentos
                    if v.medicamento_id not in meds: 
                        meds[v.medicamento_id] = {
                            'nombre': v.nombre_medicamento, 
                            'cantidad': 0, 
                            'ganancia': 0.0
                        }
                    meds[v.medicamento_id]['cantidad'] += v.cantidad_vendida
                    meds[v.medicamento_id]['ganancia'] += v.precio_total
            except ValueError:
                # Fecha mal formateada - se ignora
                pass
                
        return {
            "total_ventas": total_ventas, 
            "total_ganancias": total_ganancias, 
            "medicamentos_vendidos": meds
        }


# ============================================================
# SERVICIOS DE APLICACIÓN (Lógica de negocio)
# ============================================================

class SistemaAutenticacion:
    """
    Sistema de autenticación con protección contra ataques de fuerza bruta.
    
    Características:
    - Validación de credenciales
    - Bloqueo temporal tras 3 intentos fallidos
    - Limpieza automática de intentos antiguos
    - Manejo de campos vacíos
    
    Security features:
    - Máximo 3 intentos fallidos
    - Bloqueo de 15 minutos
    - Contador se reinicia con login exitoso
    """
    
    def __init__(self, repositorio_usuarios=None):
        """
        Inicializa el sistema de autenticación.
        
        Args:
            repositorio_usuarios (RepositorioUsuariosCSV): Inyección de dependencia
        """
        self.repositorio_usuarios = repositorio_usuarios or RepositorioUsuariosCSV()
        self.intentos_fallidos = {}  # {usuario: [timestamp1, timestamp2, ...]}
        self.max_intentos = 3
        self.bloqueo_minutos = 15
    
    def autenticar(self, nombre, password):
        """
        Autentica un usuario validando sus credenciales.
        
        Implementa protección contra fuerza bruta:
        1. Valida campos no vacíos
        2. Verifica si usuario está bloqueado
        3. Limpia intentos antiguos (>15 minutos)
        4. Compara credenciales
        5. Registra intentos fallidos
        
        Args:
            nombre (str): Nombre de usuario
            password (str): Contraseña
            
        Returns:
            tuple: (exito: bool, rol: str, error: str)
                - Si exito=True: rol contiene 'gerente'/'farmaceuta'/'vendedor'
                - Si exito=False: error contiene mensaje descriptivo
        """
        nombre = nombre.strip() if nombre else ""
        password = password.strip() if password else ""
        
        # Validar campos requeridos
        if not nombre or not password:
            return False, None, "Usuario y contraseña requeridos"
        
        # VERIFICAR SI USUARIO ESTÁ BLOQUEADO
        if nombre in self.intentos_fallidos:
            intentos = self.intentos_fallidos[nombre]
            # Limpiar intentos antiguos (mayores a 15 minutos)
            intentos = [t for t in intentos 
                       if datetime.now() - t < timedelta(minutes=self.bloqueo_minutos)]
            self.intentos_fallidos[nombre] = intentos
            
            # Si hay 3+ intentos recientes, bloquear
            if len(intentos) >= self.max_intentos:
                minutos_restantes = int(
                    (self.bloqueo_minutos * 60 - (datetime.now() - intentos[0]).total_seconds()) / 60
                )
                return False, None, f"Cuenta bloqueada por seguridad. Intenta en {minutos_restantes} minutos"
        
        # Validar credenciales
        usuario = self.repositorio_usuarios.obtener_por_id(nombre)
        
        if not usuario or usuario.password != password:
            # Registrar intento fallido
            if nombre not in self.intentos_fallidos:
                self.intentos_fallidos[nombre] = []
            self.intentos_fallidos[nombre].append(datetime.now())
            return False, None, "Usuario o contraseña incorrectos"
        
        # Login exitoso: limpiar intentos fallidos
        if nombre in self.intentos_fallidos:
            del self.intentos_fallidos[nombre]
        
        return True, usuario.rol, None


class ServicioMedicamentos:
    """
    Servicio de negocio para gestión de medicamentos.
    
    Responsabilidades:
    - Registrar nuevos medicamentos con validaciones exhaustivas
    - Buscar medicamentos por nombre, marca o ID
    - Eliminar medicamentos del inventario
    - Generar alertas de caducidad
    - Implementar caché para búsquedas frecuentes
    
    Validaciones implementadas:
    - Nombre: mínimo 3 caracteres
    - Marca: mínimo 2 caracteres
    - Precio: mayor a $0
    - Fecha: formato YYYY-MM-DD y futuro
    - Stock: no negativo
    - Duplicados: no permite medicamentos idénticos
    """
    
    def __init__(self, repositorio):
        """
        Inicializa el servicio de medicamentos.
        
        Args:
            repositorio (RepositorioMedicamentosCSV): Acceso a datos
        """
        self.repositorio = repositorio
        self._cache = {}  # {clave_busqueda: [resultados]}
        self._cache_timestamp = {}  # {clave: timestamp}
    
    def registrar_medicamento(self, nombre, precio, cantidad, fecha_caducidad, marca, 
                            precio_individual=0.0, stock=0, requiere_receta=False):
        """
        Registra un nuevo medicamento en el inventario.
        
        Valida exhaustivamente todos los campos:
        - Nombre y marca: no vacíos, longitud mínima
        - Precios: números positivos
        - Stock: entero no negativo
        - Fecha: formato válido, futuro
        - Duplicados: no existen medicamentos iguales
        
        Genera ID único con formato: M_TIMESTAMP_RANDOM
        
        Args:
            nombre (str): Nombre del medicamento
            precio (float): Precio mayorista
            cantidad (str): Presentación (500ml, 100 caps, etc)
            fecha_caducidad (str): Fecha vencimiento YYYY-MM-DD
            marca (str): Marca fabricante
            precio_individual (float): Precio venta al cliente
            stock (int): Cantidad inicial en inventario
            requiere_receta (bool): Requiere prescripción médica
            
        Returns:
            Medicamento: Medicamento registrado
            
        Raises:
            ValueError: Si alguna validación falla
        """
        nombre = nombre.strip()
        marca = marca.strip()
        
        # VALIDAR NOMBRE Y MARCA
        if not nombre or len(nombre) < 3:
            raise ValueError("El nombre debe tener al menos 3 caracteres")
        if not marca or len(marca) < 2:
            raise ValueError("La marca debe tener al menos 2 caracteres")
        
        # VALIDAR PRECIO
        try:
            precio_float = float(precio)
            if precio_float <= 0:
                raise ValueError("El precio debe ser mayor a $0")
        except ValueError:
            raise ValueError("El precio debe ser un número válido mayor a $0")
        
        # VALIDAR PRECIO INDIVIDUAL
        try:
            precio_ind_float = float(precio_individual) if precio_individual else precio_float
            if precio_ind_float <= 0:
                raise ValueError("El precio unitario debe ser mayor a $0")
        except ValueError:
            raise ValueError("El precio unitario debe ser un número válido mayor a $0")
        
        # VALIDAR STOCK
        try:
            stock_int = int(stock)
            if stock_int < 0:
                raise ValueError("El stock no puede ser negativo")
        except ValueError:
            raise ValueError("El stock debe ser un número entero no negativo")
        
        # VALIDAR FECHA
        try:
            fecha_obj = datetime.strptime(fecha_caducidad, "%Y-%m-%d")
            if fecha_obj < datetime.now():
                raise ValueError("La fecha de caducidad no puede ser en el pasado")
        except ValueError as e:
            raise ValueError(f"Fecha inválida. Use formato YYYY-MM-DD. Error: {str(e)}")
        
        # VALIDAR DUPLICADOS
        if self.repositorio.existe_duplicado(nombre, marca, cantidad):
            raise ValueError("Ya existe un medicamento con los mismos datos (nombre, marca, cantidad)")
        
        # GENERAR ID ÚNICO (no secuencial)
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        random_suffix = str(uuid.uuid4())[:8].upper()
        nuevo_id = f"M_{timestamp}_{random_suffix}"
        
        med = Medicamento(
            nuevo_id, nombre, precio_float, cantidad, fecha_caducidad, 
            marca, precio_ind_float, stock_int, requiere_receta
        )
        self.repositorio.guardar(med)
        self._limpiar_cache()
        return med
    
    def buscar_medicamentos(self, nombre=None, id_med=None, marca=None):
        """
        Busca medicamentos por múltiples criterios con soporte a caché.
        
        Soporta búsquedas parciales:
        - Por nombre: "Paracet" encuentra "Paracetamol"
        - Por marca: "Tafir" encuentra "Tafirol"
        - Por ID: búsqueda exacta
        
        Implementa caché: si se busca lo mismo, retorna resultado cacheado.
        
        Args:
            nombre (str): Parte del nombre a buscar
            id_med (str): ID exacto del medicamento
            marca (str): Parte de la marca a buscar
            
        Returns:
            list: Lista de medicamentos que coinciden
            
        Raises:
            ValueError: Si búsqueda por nombre/marca < 2 caracteres
        """
        clave = f"buscar_{nombre}_{id_med}_{marca}"
        
        # Intentar obtener del caché
        resultado_cache = self._obtener_cache(clave)
        if resultado_cache is not None:
            return resultado_cache
        
        resultados = []
        try:
            if id_med:
                m = self.repositorio.obtener_por_id(id_med)
                if m: resultados.append(m)
            if nombre:
                resultados.extend(self.repositorio.buscar_por_nombre(nombre))
            if marca:
                resultados.extend(self.repositorio.buscar_por_marca(marca))
        except ValueError as e:
            raise ValueError(str(e))
        
        # Eliminar duplicados manteniendo orden
        resultado_limpio = list({m.id_medicamento: m for m in resultados}.values())
        
        # Guardar en caché
        self._guardar_cache(clave, resultado_limpio)
        
        return resultado_limpio
    
    def eliminar_medicamento(self, id_med):
        """
        Elimina un medicamento del inventario.
        
        Args:
            id_med (str): ID del medicamento a eliminar
        """
        self.repositorio.eliminar(id_med)
        self._limpiar_cache()
    
    def obtener_proximos_a_caducar(self, dias=30):
        """
        Obtiene medicamentos próximos a caducar.
        
        Usado por farmacéuticos para generar alertas.
        
        Args:
            dias (int): Días a futuro (default: 30)
            
        Returns:
            list: Medicamentos próximos a caducar
        """
        return self.repositorio.obtener_proximos_a_caducar(dias)
    
    def _obtener_cache(self, clave, maxage_segundos=300):
        """
        Obtiene un resultado cacheado si no está expirado.
        
        Args:
            clave (str): Clave de búsqueda
            maxage_segundos (int): Máxima edad del caché (default: 5 minutos)
            
        Returns:
            list o None: Resultado si existe y es válido, None si expiró
        """
        if clave in self._cache:
            timestamp = self._cache_timestamp.get(clave, 0)
            if (datetime.now().timestamp() - timestamp) < maxage_segundos:
                return self._cache[clave]
        return None
    
    def _guardar_cache(self, clave, valor):
        """Guarda un resultado en el caché."""
        self._cache[clave] = valor
        self._cache_timestamp[clave] = datetime.now().timestamp()
    
    def _limpiar_cache(self):
        """Limpia completamente el caché (se usa cuando se modifica inventario)."""
        self._cache.clear()
        self._cache_timestamp.clear()


class ServicioVentas:
    """
    Servicio de negocio para gestión de ventas.
    
    Responsabilidades:
    - Registrar transacciones de venta
    - Validar stock disponible
    - Descontar stock automáticamente
    - Guardar información de recetas
    - Generar reportes de ventas
    
    Características de seguridad:
    - Validación exhaustiva de datos
    - Control de stock antes de vender
    - Persistencia inmediata de cambios
    - Auditoría completa de transacciones
    """
    
    def __init__(self, repositorio_ventas, repositorio_medicamentos):
        """
        Inicializa el servicio de ventas.
        
        Args:
            repositorio_ventas (RepositorioVentasCSV): Acceso a historial
            repositorio_medicamentos (RepositorioMedicamentosCSV): Acceso a inventario
        """
        self.repositorio_ventas = repositorio_ventas
        self.repositorio_medicamentos = repositorio_medicamentos
    
    def registrar_venta(self, medicamento_id, cantidad, empleado, receta=""):
        """
        Registra una transacción de venta con validaciones y control de stock.
        
        Proceso:
        1. Valida que medicamento existe
        2. Valida cantidad (número positivo)
        3. Valida stock disponible (PREVIENE OVERSELL)
        4. Descuenta stock inmediatamente
        5. Registra venta en historial
        
        Args:
            medicamento_id (str): ID del medicamento
            cantidad (int): Cantidad a vender
            empleado (str): Nombre del vendedor
            receta (str): Datos de receta médica si aplica
            
        Returns:
            Venta: Transacción registrada
            
        Raises:
            ValueError: Si validación falla (stock insuficiente, med no existe, etc)
        """
        medicamento_id = medicamento_id.strip()
        empleado = empleado.strip()
        
        # VALIDAR MEDICAMENTO EXISTE
        med = self.repositorio_medicamentos.obtener_por_id(medicamento_id)
        if not med:
            raise ValueError(f"Medicamento {medicamento_id} no existe.")
        
        # VALIDAR CANTIDAD
        try:
            cantidad_int = int(cantidad)
            if cantidad_int <= 0:
                raise ValueError("La cantidad debe ser mayor a 0")
        except ValueError:
            raise ValueError("La cantidad debe ser un número entero positivo")
        
        # VALIDAR STOCK DISPONIBLE (CRITICAMENTE IMPORTANTE)
        if int(med.stock) < cantidad_int:
            raise ValueError(f"Stock insuficiente para {med.nombre}. Disponible: {med.stock}, Solicitado: {cantidad_int}")
        
        # DESCONTAR STOCK INMEDIATAMENTE (antes de registrar venta)
        med.stock = int(med.stock) - cantidad_int
        self.repositorio_medicamentos.actualizar(med)
        
        # GENERAR ID SECUENCIAL PARA VENTA
        max_id = max(
            [int(v.id_venta.split("_")[1]) for v in self.repositorio_ventas.obtener_todos() 
             if v.id_venta.startswith("V_")] + [0]
        )
        nuevo_id = f"V_{max_id + 1}"
        
        # CALCULAR TOTAL
        precio_total = med.precio_individual * cantidad_int
        
        # CREAR Y GUARDAR VENTA
        venta = Venta(
            nuevo_id, 
            medicamento_id, 
            med.nombre, 
            cantidad_int, 
            med.precio_individual, 
            precio_total,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
            empleado,
            receta  # Guardar receta si aplica
        )
        
        self.repositorio_ventas.guardar(venta)
        
        return venta
    
    def obtener_estadisticas_semanales(self):
        """
        Obtiene estadísticas de ventas de los últimos 7 días.
        
        Returns:
            dict: Estadísticas del período
        """
        return self.repositorio_ventas.obtener_estadisticas_semanales()
    
    def obtener_todas_ventas(self):
        """
        Obtiene el historial completo de ventas.
        
        Returns:
            list: Todas las transacciones
        """
        return self.repositorio_ventas.obtener_todos()
import sys
import os

# --- CONFIGURACIÓN GLOBAL DE RUTAS ---

# 1. Obtenemos la ruta de la carpeta actual (tests/)
current_dir = os.path.dirname(os.path.abspath(__file__))

# 2. Obtenemos la raíz del proyecto (D:\Proyecto_Horarios)
project_root = os.path.dirname(current_dir)

# 3. Obtenemos la ruta del código fuente (D:\Proyecto_Horarios\Proyecto)
src_dir = os.path.join(project_root, "Proyecto")

# AÑADIMOS LAS RUTAS AL SISTEMA:

# Para que los tests puedan hacer: "from Proyecto.archivo import ..."
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Para que los archivos DENTRO de Proyecto puedan importarse entre sí
# (ej: que extractor_pdf encuentre a validacion)
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)
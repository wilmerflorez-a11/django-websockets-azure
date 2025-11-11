from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Q
from .models import Documento, PermisoDocumento

def login_view(request):
    """Vista de login"""
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            messages.success(request, f'¡Bienvenido {user.username}!')
            return redirect('dashboard')
        else:
            messages.error(request, 'Usuario o contraseña incorrectos')
    
    return render(request, 'editor/login.html')

def register_view(request):
    """Vista de registro"""
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        password2 = request.POST.get('password2')
        
        # Validaciones
        if password != password2:
            messages.error(request, 'Las contraseñas no coinciden')
        elif User.objects.filter(username=username).exists():
            messages.error(request, 'El nombre de usuario ya existe')
        elif User.objects.filter(email=email).exists():
            messages.error(request, 'El email ya está registrado')
        elif len(password) < 6:
            messages.error(request, 'La contraseña debe tener al menos 6 caracteres')
        else:
            # Crear usuario
            user = User.objects.create_user(username=username, email=email, password=password)
            login(request, user)
            messages.success(request, f'¡Cuenta creada exitosamente! Bienvenido {username}')
            return redirect('dashboard')
    
    return render(request, 'editor/register.html')

def logout_view(request):
    """Vista de logout"""
    logout(request)
    messages.success(request, 'Sesión cerrada exitosamente')
    return redirect('login')

@login_required
def dashboard(request):
    """Dashboard con documentos del usuario"""
    # Documentos propios
    documentos_propios = Documento.objects.filter(propietario=request.user)
    
    # Documentos compartidos conmigo
    documentos_compartidos = Documento.objects.filter(
        permisos__usuario=request.user
    ).distinct()
    
    return render(request, 'editor/dashboard.html', {
        'documentos_propios': documentos_propios,
        'documentos_compartidos': documentos_compartidos,
    })

@login_required
def crear_documento(request):
    """Crear nuevo documento"""
    if request.method == 'POST':
        titulo = request.POST.get('titulo', 'Documento sin título')
        contenido = request.POST.get('contenido', '')
        
        documento = Documento.objects.create(
            titulo=titulo,
            contenido=contenido,
            propietario=request.user
        )
        messages.success(request, f'Documento "{titulo}" creado exitosamente')
        return redirect('documento', doc_id=documento.id)
    
    return render(request, 'editor/crear_documento.html')

@login_required
def documento(request, doc_id):
    """Vista del editor de documento"""
    doc = get_object_or_404(Documento, id=doc_id)
    
    # Verificar permisos
    if not doc.puede_ver(request.user):
        messages.error(request, 'No tienes permiso para ver este documento')
        return redirect('dashboard')
    
    # Verificar si puede editar
    puede_editar = doc.puede_editar(request.user)
    
    # Obtener usuarios con permisos
    permisos = PermisoDocumento.objects.filter(documento=doc).select_related('usuario')
    
    return render(request, 'editor/documento.html', {
        'documento': doc,
        'puede_editar': puede_editar,
        'es_propietario': doc.propietario == request.user,
        'permisos': permisos,
    })

@login_required
def compartir_documento(request, doc_id):
    """Compartir documento con otro usuario"""
    doc = get_object_or_404(Documento, id=doc_id)
    
    # Solo el propietario puede compartir
    if doc.propietario != request.user:
        messages.error(request, 'Solo el propietario puede compartir este documento')
        return redirect('documento', doc_id=doc_id)
    
    if request.method == 'POST':
        username = request.POST.get('username')
        puede_editar = request.POST.get('puede_editar') == 'on'
        
        try:
            usuario = User.objects.get(username=username)
            
            # No compartir consigo mismo
            if usuario == request.user:
                messages.error(request, 'No puedes compartir el documento contigo mismo')
            else:
                # Crear o actualizar permiso
                permiso, created = PermisoDocumento.objects.get_or_create(
                    documento=doc,
                    usuario=usuario,
                    defaults={
                        'puede_editar': puede_editar,
                        'compartido_por': request.user
                    }
                )
                
                if not created:
                    permiso.puede_editar = puede_editar
                    permiso.save()
                    messages.success(request, f'Permisos actualizados para {username}')
                else:
                    messages.success(request, f'Documento compartido con {username}')
        
        except User.DoesNotExist:
            messages.error(request, f'El usuario "{username}" no existe')
        
        return redirect('documento', doc_id=doc_id)
    
    # GET: Listar todos los usuarios disponibles
    usuarios_disponibles = User.objects.exclude(id=request.user.id)
    
    return render(request, 'editor/compartir.html', {
        'documento': doc,
        'usuarios_disponibles': usuarios_disponibles,
    })

@login_required
def eliminar_permiso(request, doc_id, permiso_id):
    """Eliminar permiso de un usuario"""
    doc = get_object_or_404(Documento, id=doc_id)
    
    # Solo el propietario puede eliminar permisos
    if doc.propietario != request.user:
        messages.error(request, 'No tienes permiso para realizar esta acción')
        return redirect('documento', doc_id=doc_id)
    
    permiso = get_object_or_404(PermisoDocumento, id=permiso_id, documento=doc)
    username = permiso.usuario.username
    permiso.delete()
    
    messages.success(request, f'Permiso revocado para {username}')
    return redirect('documento', doc_id=doc_id)

@login_required
def eliminar_documento(request, doc_id):
    """Eliminar documento (solo propietario)"""
    doc = get_object_or_404(Documento, id=doc_id)
    
    if doc.propietario != request.user:
        messages.error(request, 'Solo el propietario puede eliminar este documento')
        return redirect('dashboard')
    
    if request.method == 'POST':
        titulo = doc.titulo
        doc.delete()
        messages.success(request, f'Documento "{titulo}" eliminado exitosamente')
        return redirect('dashboard')
    
    return render(request, 'editor/eliminar_documento.html', {'documento': doc})
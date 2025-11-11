import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'proyecto.settings')
django.setup()

from django.contrib.auth.models import User
from editor.models import Documento, PermisoDocumento

print("🚀 Configurando usuarios y documentos de prueba...\n")

# Crear usuarios de prueba
usuarios_data = [
    {'username': 'alice', 'email': 'alice@example.com', 'password': 'alice123'},
    {'username': 'bob', 'email': 'bob@example.com', 'password': 'bob123'},
    {'username': 'charlie', 'email': 'charlie@example.com', 'password': 'charlie123'},
]

usuarios = {}
for data in usuarios_data:
    user, created = User.objects.get_or_create(
        username=data['username'],
        defaults={'email': data['email']}
    )
    if created:
        user.set_password(data['password'])
        user.save()
        print(f"✅ Usuario creado: {data['username']} (contraseña: {data['password']})")
    else:
        print(f"⏭️  Usuario ya existe: {data['username']}")
    usuarios[data['username']] = user

print()

# Crear documentos de prueba
if 'alice' in usuarios:
    doc1, created = Documento.objects.get_or_create(
        titulo="Proyecto Colaborativo 2025",
        propietario=usuarios['alice'],
        defaults={'contenido': 'Este es un documento donde todos pueden colaborar.'}
    )
    if created:
        print(f"✅ Documento creado: {doc1.titulo} (Propietario: Alice)")
        
        # Compartir con Bob (puede editar)
        if 'bob' in usuarios:
            PermisoDocumento.objects.get_or_create(
                documento=doc1,
                usuario=usuarios['bob'],
                defaults={'puede_editar': True, 'compartido_por': usuarios['alice']}
            )
            print(f"   🤝 Compartido con Bob (puede editar)")
        
        # Compartir con Charlie (solo lectura)
        if 'charlie' in usuarios:
            PermisoDocumento.objects.get_or_create(
                documento=doc1,
                usuario=usuarios['charlie'],
                defaults={'puede_editar': False, 'compartido_por': usuarios['alice']}
            )
            print(f"   🤝 Compartido con Charlie (solo lectura)")

    doc2, created = Documento.objects.get_or_create(
        titulo="Notas Personales de Alice",
        propietario=usuarios['alice'],
        defaults={'contenido': 'Estas son mis notas privadas.'}
    )
    if created:
        print(f"✅ Documento creado: {doc2.titulo} (Propietario: Alice)")

if 'bob' in usuarios:
    doc3, created = Documento.objects.get_or_create(
        titulo="Ideas de Bob",
        propietario=usuarios['bob'],
        defaults={'contenido': 'Aquí guardo mis ideas brillantes.'}
    )
    if created:
        print(f"✅ Documento creado: {doc3.titulo} (Propietario: Bob)")

print("\n" + "="*60)
print("✨ Configuración completada!")
print("="*60)
print("\n📝 Usuarios creados:")
print("-" * 60)
for data in usuarios_data:
    print(f"  Usuario: {data['username']:10} | Contraseña: {data['password']}")
print("-" * 60)
print("\n🌐 Accede a: http://localhost:8000/")
print("💡 Inicia sesión con cualquiera de los usuarios de arriba\n")
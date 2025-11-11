from django.db import models
from django.contrib.auth.models import User

class Documento(models.Model):
    titulo = models.CharField(max_length=100)
    contenido = models.TextField(blank=True)
    propietario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='documentos_propios')
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.titulo} ({self.propietario.username})"
    
    class Meta:
        verbose_name = "Documento"
        verbose_name_plural = "Documentos"
        ordering = ['-actualizado']
    
    def puede_editar(self, usuario):
        """Verifica si un usuario puede editar este documento"""
        # El propietario siempre puede editar
        if self.propietario == usuario:
            return True
        # Verificar si tiene permiso compartido de escritura
        return PermisoDocumento.objects.filter(
            documento=self,
            usuario=usuario,
            puede_editar=True
        ).exists()
    
    def puede_ver(self, usuario):
        """Verifica si un usuario puede ver este documento"""
        # El propietario siempre puede ver
        if self.propietario == usuario:
            return True
        # Verificar si tiene algún permiso compartido
        return PermisoDocumento.objects.filter(
            documento=self,
            usuario=usuario
        ).exists()


class PermisoDocumento(models.Model):
    documento = models.ForeignKey(Documento, on_delete=models.CASCADE, related_name='permisos')
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='documentos_compartidos')
    puede_editar = models.BooleanField(default=False)
    compartido_por = models.ForeignKey(User, on_delete=models.CASCADE, related_name='permisos_otorgados')
    fecha_compartido = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Permiso de Documento"
        verbose_name_plural = "Permisos de Documentos"
        unique_together = ['documento', 'usuario']
        ordering = ['-fecha_compartido']
    
    def __str__(self):
        permiso = "Editar" if self.puede_editar else "Solo lectura"
        return f"{self.documento.titulo} → {self.usuario.username} ({permiso})"
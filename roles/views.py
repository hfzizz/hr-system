from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib import messages
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType

class RoleListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = Group
    template_name = 'roles/role_list.html'
    context_object_name = 'roles'
    permission_required = 'auth.view_group'

class RoleCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = Group
    template_name = 'roles/role_form.html'
    fields = ['name']
    success_url = reverse_lazy('roles:list')
    permission_required = 'auth.add_group'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Create Role'
        context['permission_categories'] = self.get_permission_categories()
        return context

    def get_permission_categories(self):
        categories = {}
        relevant_apps = ['employees', 'appraisals', 'auth']  # Add your app names here
        
        for app in relevant_apps:
            content_types = ContentType.objects.filter(app_label=app)
            
            for ct in content_types:
                model_name = ct.model.replace('_', ' ').title()
                if app not in categories:
                    categories[app] = {
                        'title': app.title(),
                        'permissions': []
                    }
                
                perms = Permission.objects.filter(content_type=ct)
                for perm in perms:
                    # Make permission names more readable
                    codename = perm.codename
                    if codename.startswith('view'):
                        action = 'View'
                    elif codename.startswith('add'):
                        action = 'Add'
                    elif codename.startswith('change'):
                        action = 'Edit'
                    elif codename.startswith('delete'):
                        action = 'Delete'
                    else:
                        action = codename.replace('_', ' ').title()
                    
                    readable_name = f"{action} {model_name}"
                    
                    categories[app]['permissions'].append({
                        'id': perm.id,
                        'name': readable_name,
                        'codename': perm.codename,
                        'checked': False if not self.object else perm in self.object.permissions.all()
                    })
                
            # Remove empty categories
            categories = {k: v for k, v in categories.items() if v['permissions']}
        
        return categories

    def form_valid(self, form):
        response = super().form_valid(form)
        # Handle permissions
        permissions = self.request.POST.getlist('permissions')
        self.object.permissions.set(permissions)
        return response

class RoleUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = Group
    template_name = 'roles/role_form.html'
    fields = ['name']
    success_url = reverse_lazy('roles:list')
    permission_required = 'auth.change_group'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Edit Role'
        context['permission_categories'] = self.get_permission_categories()
        return context

    def get_permission_categories(self):
        categories = {}
        relevant_apps = ['employees', 'appraisals', 'auth']  # Add your app names here
        
        for app in relevant_apps:
            content_types = ContentType.objects.filter(app_label=app)
            
            for ct in content_types:
                model_name = ct.model.replace('_', ' ').title()
                if app not in categories:
                    categories[app] = {
                        'title': app.title(),
                        'permissions': []
                    }
                
                perms = Permission.objects.filter(content_type=ct)
                for perm in perms:
                    # Make permission names more readable
                    codename = perm.codename
                    if codename.startswith('view'):
                        action = 'View'
                    elif codename.startswith('add'):
                        action = 'Add'
                    elif codename.startswith('change'):
                        action = 'Edit'
                    elif codename.startswith('delete'):
                        action = 'Delete'
                    else:
                        action = codename.replace('_', ' ').title()
                    
                    readable_name = f"{action} {model_name}"
                    
                    categories[app]['permissions'].append({
                        'id': perm.id,
                        'name': readable_name,
                        'codename': perm.codename,
                        'checked': perm in self.object.permissions.all()
                    })
                
            # Remove empty categories
            categories = {k: v for k, v in categories.items() if v['permissions']}
        
        return categories

    def form_valid(self, form):
        response = super().form_valid(form)
        # Handle permissions
        permissions = self.request.POST.getlist('permissions')
        self.object.permissions.set(permissions)
        return response

class RoleDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = Group
    template_name = 'roles/role_confirm_delete.html'
    success_url = reverse_lazy('roles:list')
    permission_required = 'auth.delete_group'

from django.contrib.auth.backends import ModelBackend


class ObjectPermissionsBackend(ModelBackend):  # (object)

    # super implementation of has_perm:
    # def has_perm(self, user_obj, perm, obj=None):
    #     return perm in self.get_all_permissions(user_obj, obj=obj)

    # return user_obj.is_active and super().has_perm(user_obj, perm, obj=obj)

    def has_perm(self, user_obj, perm, obj=None):
        print("=== def has_perm() =======================================")

        if not user_obj.is_active:
            return False

        # if not obj:
        #     return False # not dealing with non-object permissions

        return True

        # if perm == 'view':
        #     return True # anyone can view

        # if obj and obj.tenant == self.request.tenant:
        #     return True

        # return False

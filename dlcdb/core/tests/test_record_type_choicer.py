# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

import pytest


"""

    def get_proxy_instance(self):
   
        Return the concrete proxy model instance
   
        modelclass = self.get_type()['get_proxy_model']()
        # query the concrete proy model instance
        return modelclass.objects.select_related('room', 'device').get(id=self.id)


        return Record.TYPE_CHOICER.get_choices()

            def get_queryset(self):
        return super(Manager, self).get_queryset().filter(
            type=Record.TYPE_CHOICER.ENUMS.destroyed
        )

         label=obj.get_record_type_display()
"""


@pytest.mark.django_db
def test_is_active(room, lentable_device):
    pass

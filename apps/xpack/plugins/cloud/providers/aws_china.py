# -*- coding: utf-8 -*-
#
from django.utils.translation import ugettext_lazy as _
from . import aws_international


class Provider(aws_international.Provider):

    def _is_valid(self):
        self.get_instances_of_region(region_id='cn-north-1')

    def get_region_ids(self):
        region_ids = self.session.get_available_regions(service_name='ec2', partition_name='aws-cn')
        return region_ids

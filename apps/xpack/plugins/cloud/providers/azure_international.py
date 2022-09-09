
from . import azure as azure_china


class Provider(azure_china.Provider):

    authentication_endpoint = 'https://login.microsoftonline.com/'
    azure_endpoint = 'https://management.azure.com/'

    def get_regions(self):
        regions = self.subscription_client.subscriptions.list_locations(self.subscription_id)
        regions = {region.name: region.display_name for region in regions}
        return regions

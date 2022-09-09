from rest_framework.routers import DefaultRouter

from .. import api

router = DefaultRouter()
router.register('setting', api.InterfaceViewSet, 'setting')

urlpatterns = router.urls

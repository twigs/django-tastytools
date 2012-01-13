from django.db.models.fields.related import ManyToManyField
from django.db.models.fields.related import ForeignRelatedObjectsDescriptor

class Related(object):
    '''Constants holder class for various types of data generation modes'''

    Model = "MODEL"
    Uri = "URI"
    Full = "FULL"


class ResourceTestData(object):

    def __init__(self, api, resource=None):
        '''Constructor - requires the resource name or class to be registered
        on the given api.'''

        if resource is None:
            msg = "ResourceTestData initialized without a resource. "\
                "Did you forget to override the constructor?"
            raise Exception(msg)

        self.api = api
        if type(resource) is str:
            resource = self.api.resources[resource]
        self.resource = resource

    @property
    def post(self):
        '''Returns sample POST data for the resource.'''

        return self.sample_data(related=Related.Uri).data

    @property
    def get(self):
        '''Returns sample GET data for the resource.'''

        (location, model) = self.create_test_resource()
        return self.api.dehydrate(resource=self.resource, obj=model)

    def create_test_resource(self, force={}, *args, **kwargs):
        '''Creates a test resource and obtains it's URI
        and related object'''

        model = self.create_test_model(force=force, *args, **kwargs)
        bundle = self.resource.build_bundle(obj=model)
        location = self.resource.get_resource_uri(bundle)
        return location, bundle.obj

    def create_test_model(self, data=False, force=False, *args, **kwargs):
        '''Creates a test model (or object asociated with
        the resource and returns it'''

        force = force or {}

        data = data or self.sample_data(related=Related.Model, force=force)
        model_class = self.resource._meta.object_class

        valid_data = {}
        m2m = {}
        class_fields = model_class._meta.get_all_field_names()
        for field in class_fields:
            try:
                valid_data[field] = data[field]

                try:
                    field_obj = model_class._meta.get_field(field)
                    is_m2m = isinstance(field_obj, ManyToManyField)
                except Exception:
                    field_obj = getattr(model_class, field)
                    is_m2m = isinstance(field_obj,
                        ForeignRelatedObjectsDescriptor)

                if is_m2m:
                    m2m[field] = data[field]
                    del valid_data[field]

            except KeyError:
                pass

        model = model_class(**valid_data)
        model.save()
        for m2m_field, values in m2m.items():
            for value in values:
                getattr(model, m2m_field).add(value)

        return model

    @property
    def sample_data(self):
        '''Returns the full a full set of data as an example for
        interacting with the resource'''

        return {}


class TestData(object):

    def __init__(self, api, force, related):
        self.api = api
        self.force = force or {}
        self.related = related
        self.data = {}

    def __getitem__(self, name):
        return self.data[name]

    def __setitem__(self, name, value):
        self.data[name] = value

    def __delitem__(self, name):
        del self.data[name]

    def update(self, data):
        return self.data.update(data)

    def to_dict(self):
        return self.data

    def set(self, name, constant=None, resource=None, count=None,
        force=False):

        value = None
        force = force or {}

        if name in self.force:
            value = self.force[name]
        elif resource is not None:
            if count > 0:
                value = []
                while count > 0:
                    res = self.create_test_data(resource,
                        related=self.related, force=force)
                    value.append(res)
                    count -= 1
            else:
                value = self.create_test_data(resource,
                    related=self.related, force=force)
        elif constant is not None:
            value = constant
        else:
            raise Exception("Expected resource or constant")

        self.data[name] = value

        return value

    def create_test_data(self, resource_name, related=Related.Model,
        force=False):
        force = force or {}

        resource = self.api.resources[resource_name]

        (uri, res) = resource.create_test_resource(force)

        if related == Related.Uri:
            return uri
        elif related == Related.Model:
            return res
        elif related == Related.Full:
            return self.api.dehydrate(resource=resource_name, obj=res)

        raise Exception("Missing desired related type. Given: %s" % related)
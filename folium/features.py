# -*- coding: utf-8 -*-
"""
Elements
------

A generic class for creating Elements.
"""
import warnings
from uuid import uuid4

from jinja2 import Environment, PackageLoader, Template
ENV = Environment(loader=PackageLoader('folium', 'templates'))
from collections import OrderedDict
import json

from .six import text_type, binary_type, urlopen
from .utilities import color_brewer

def _camelify(out):
    return (''.join(["_"+x.lower() if i<len(out)-1 and x.isupper() and out[i+1].islower()
         else x.lower()+"_" if i<len(out)-1 and x.islower() and out[i+1].isupper()
         else x.lower() for i,x in enumerate(list(out))])).lstrip('_').replace('__','_')

class Element(object):
    """Basic Element object that does nothing.
    Other Elements may inherit from this one."""
    def __init__(self, template=None, template_name=None):
        """Creates a Element."""
        self._name = 'Element'
        self._id = uuid4().hex
        self._env = ENV
        self._children = OrderedDict()
        self._parent = None
        self._template = Template(template) if template is not None\
            else ENV.get_template(template_name) if template_name is not None\
            else Template(u"""
        {% for name, element in this._children.items() %}
            {{element.render(**kwargs)}}
        {% endfor %}
        """)

    def get_name(self):
        return _camelify(self._name) + '_' +self._id

    def add_children(self, child, name=None, index=None):
        """Add a children."""
        if name is None:
            name = child.get_name()
        if index is None:
            self._children[name] = child
        else:
            items = [item for item in self._children.items() if item[0] != name]
            items.insert(int(index),(name,child))
            self._children = items
        child._parent = self

    def add_to(self, parent, name=None, index=None):
        """Add element to a parent."""
        parent.add_children(self, name=name, index=index)

    def to_dict(self, depth=-1, ordered=True, **kwargs):
        if ordered:
            dict_fun = OrderedDict
        else:
            dict_fun = dict
        out = dict_fun()
        out['name'] = self._name
        out['id'] = self._id
        if depth != 0:
            out['children'] = dict_fun([(name, child.to_dict(depth=depth-1))\
                    for name,child in self._children.items()])
        return out

    def to_json(self, depth=-1, **kwargs):
        return json.dumps(self.to_dict(depth=depth, ordered=True), **kwargs)

    def get_root(self):
        """Returns the root of the elements tree."""
        if self._parent is None:
            return self
        else:
            return self._parent.get_root()

    def render(self, **kwargs):
        """TODO : docstring here."""
        return self._template.render(this=self, kwargs=kwargs)

_default_js = [
    ('leaflet',
     "https://cdnjs.cloudflare.com/ajax/libs/leaflet/0.7.3/leaflet.js"),
    ('jquery',
     "https://ajax.googleapis.com/ajax/libs/jquery/1.11.1/jquery.min.js"),
    ('bootstrap',
     "https://maxcdn.bootstrapcdn.com/bootstrap/3.2.0/js/bootstrap.min.js"),
    ('awesome_markers',
     "https://rawgithub.com/lvoogdt/Leaflet.awesome-markers/2.0/develop/dist/leaflet.awesome-markers.js"),
    ('marker_cluster_src',
     "https://cdnjs.cloudflare.com/ajax/libs/leaflet.markercluster/0.4.0/leaflet.markercluster-src.js"),
    ('marker_cluster',
     "https://cdnjs.cloudflare.com/ajax/libs/leaflet.markercluster/0.4.0/leaflet.markercluster.js"),
    ]

_default_css = [
    ("leaflet_css",
     "https://cdnjs.cloudflare.com/ajax/libs/leaflet/0.7.3/leaflet.css"),
    ("bootstrap_css",
     "https://maxcdn.bootstrapcdn.com/bootstrap/3.2.0/css/bootstrap.min.css"),
    ("bootstrap_theme_css",
     "https://maxcdn.bootstrapcdn.com/bootstrap/3.2.0/css/bootstrap-theme.min.css"),
    ("awesome_markers_font_css",
     "https://maxcdn.bootstrapcdn.com/font-awesome/4.1.0/css/font-awesome.min.css"),
    ("awesome_markers_css",
     "https://rawgit.com/lvoogdt/Leaflet.awesome-markers/2.0/develop/dist/leaflet.awesome-markers.css"),
    ("marker_cluster_default_css",
     "https://cdnjs.cloudflare.com/ajax/libs/leaflet.markercluster/0.4.0/MarkerCluster.Default.css"),
    ("marker_cluster_css",
     "https://cdnjs.cloudflare.com/ajax/libs/leaflet.markercluster/0.4.0/MarkerCluster.css"),
    ("awesome_rotate_css",
     "https://raw.githubusercontent.com/python-visualization/folium/master/folium/templates/leaflet.awesome.rotate.css"),
    ]

class Figure(Element):
    def __init__(self):
        super(Figure, self).__init__()
        self._name = 'Figure'
        self.header = Element()
        self.html   = Element()
        self.script = Element()
        #self.axes = []

        self.header._parent = self
        self.html._parent = self
        self.script._parent = self

        self._template = Template(u"""
        <!DOCTYPE html>
        <head>
            {{this.header.render(**kwargs)}}
        </head>
        <body>
            {{this.html.render(**kwargs)}}
        </body>
        <script>
            {{this.script.render(**kwargs)}}
        </script>
        """)

        # Create the meta tag
        self.header.add_children(Element(
            '<meta http-equiv="content-type" content="text/html; charset=UTF-8" />'),
                                  name='meta_http')

        # Import Javascripts
        for name, url in _default_js:
            self.header.add_children(JavascriptLink(url), name=name)

        # Import Css
        for name, url in _default_css:
            self.header.add_children(CssLink(url), name=name)

        self.header.add_children(Element("""
            <style>

            html, body {
                width: 100%;
                height: 100%;
                margin: 0;
                padding: 0;
                }

            #map {
                position:absolute;
                top:0;
                bottom:0;
                right:0;
                left:0;
                }
            </style>
            """), name='css_style')

    def to_dict(self, depth=-1, **kwargs):
        out = super(Figure, self).to_dict(depth=depth, **kwargs)
        out['header'] = self.header.to_dict(depth=depth-1, **kwargs)
        out['html'] = self.html.to_dict(depth=depth-1, **kwargs)
        out['script'] = self.script.to_dict(depth=depth-1, **kwargs)
        return out

    def render(self, **kwargs):
        """TODO : docstring here."""
        for name, child in self._children.items():
            child.render(**kwargs)
        return self._template.render(this=self, kwargs=kwargs)

    def _repr_html_(self, figsize=(17,10), **kwargs):
        """Displays the Figure in a Jupyter notebook.

        Parameters
        ----------
            self : folium.Map object
                The map you want to display

            figsize : tuple of length 2, default (17,10)
                The size of the output you expect in inches.
                Output is 60dpi so that the output has same size as a
                matplotlib figure with the same figsize.

        """
        html = self.render(**kwargs)

        width, height = figsize

        iframe = '<iframe src="{html}" width="{width}px" height="{height}px"></iframe>'\
            .format(\
                    html = "data:text/html;base64,"+html.encode('utf8').encode('base64'),
                    #html = self.HTML.replace('"','&quot;'),
                    width = int(60.*width),
                    height= int(60.*height),
                   )
        return iframe

    def add_subplot(self, x,y,n,margin=0.05):
        width = 1./y
        height = 1./x
        left = ((n-1)%y)*width
        top = ((n-1)//y)*height

        left = left+width*margin
        top  = top+height*margin
        width = width*(1-2.*margin)
        height = height*(1-2.*margin)

        div = Div(position='absolute',
                  width="{}%".format(100.*width),
                  height="{}%".format(100.*height),
                  left="{}%".format(100.*left),
                  top="{}%".format(100.*top),
                  )
        self.add_children(div)
        return div

class Link(Element):
    def get_code(self):
        if self.code is None:
            self.code = urlopen(self.url).read()
        return self.code
    def to_dict(self, depth=-1, **kwargs):
        out = super(Link, self).to_dict(depth=-1, **kwargs)
        out['url'] = self.url
        return out

class JavascriptLink(Link):
    def __init__(self, url, download=False):
        """Create a JavascriptLink object based on a url.
        Parameters
        ----------
            url : str
                The url to be linked
            download : bool, default False
                Whether the target document shall be loaded right now.
        """
        super(JavascriptLink, self).__init__()
        self._name = 'JavascriptLink'
        self.url = url
        self.code = None
        if download:
            self.get_code()

        self._template = Template(u"""
        {% if kwargs.get("embedded",False) %}
            <script>{{this.get_code()}}</script>
        {% else %}
            <script src="{{this.url}}"></script>
        {% endif %}
        """)

class CssLink(Link):
    def __init__(self, url, download=False):
        """Create a CssLink object based on a url.
        Parameters
        ----------
            url : str
                The url to be linked
            download : bool, default False
                Whether the target document shall be loaded right now.
        """
        super(CssLink, self).__init__()
        self._name = 'CssLink'
        self.url = url
        self.code = None
        if download:
            self.get_code()

        self._template = Template(u"""
        {% if kwargs.get("embedded",False) %}
            <style>{{this.get_code()}}</style>
        {% else %}
            <link rel="stylesheet" href="{{this.url}}" />
        {% endif %}
        """)

class Div(Figure):
    def __init__(self, width='100%', height='100%',
                 left="0%", top="0%", position='relative'):
        """Create a Map with Folium and Leaflet.js
        """
        super(Figure, self).__init__()
        self._name = 'Div'

        # Size Parameters.
        self.width  = _parse_size(width)
        self.height = _parse_size(height)
        self.left = _parse_size(left)
        self.top  = _parse_size(top)
        self.position = position

        self.header = Element()
        self.html   = Element("""
        {% for name, element in this._children.items() %}
            {{element.render(**kwargs)}}
        {% endfor %}
        """)
        self.script = Element()

        self.header._parent = self
        self.html._parent = self
        self.script._parent = self

        self._template = Template(u"""
        {% macro header(this, kwargs) %}
            <style> #{{this.get_name()}} {
                position : {{this.position}};
                width : {{this.width[0]}}{{this.width[1]}};
                height: {{this.height[0]}}{{this.height[1]}};
                left: {{this.left[0]}}{{this.left[1]}};
                top: {{this.top[0]}}{{this.top[1]}};
            </style>
        {% endmacro %}
        {% macro html(this, kwargs) %}
            <div id="{{this.get_name()}}">
                {{this.html.render(**kwargs)}}
            </div>
        {% endmacro %}
        """)

    def get_root(self):
        return self

    def render(self, **kwargs):
        """TODO : docstring here."""
        figure = self._parent
        assert isinstance(figure,Figure), ("You cannot render this Element "
            "if it's not in a Figure.")

        for name, element in self._children.items():
            element.render(**kwargs)

        for name, element in self.header._children.items():
            figure.header.add_children(element, name=name)

        for name, element in self.script._children.items():
            figure.script.add_children(element, name=name)

        header = self._template.module.__dict__.get('header',None)
        if header is not None:
            figure.header.add_children(Element(header(self, kwargs)),
                                       name=self.get_name())

        html = self._template.module.__dict__.get('html',None)
        if html is not None:
            figure.html.add_children(Element(html(self, kwargs)),
                                       name=self.get_name())

        script = self._template.module.__dict__.get('script',None)
        if script is not None:
            figure.script.add_children(Element(script(self, kwargs)),
                                       name=self.get_name())

def _repr_html_(self, figsize=(17,10), **kwargs):
        """Displays the Map in a Jupyter notebook.

        Parameters
        ----------
            self : folium.Map object
                The map you want to display

            figsize : tuple of length 2, default (17,10)
                The size of the output you expect in inches.
                Output is 60dpi so that the output has same size as a
                matplotlib figure with the same figsize.

        """
        if self._parent is None:
            self.add_to(Figure())
            out = self._parent._repr_html_(figsize=figsize, **kwargs)
            self._parent = None
        else:
            out = self._parent._repr_html_(figsize=figsize, **kwargs)
        return out

class MacroElement(Element):
    """This is a parent class for Elements defined by a macro template.
    To compute your own element, all you have to do is:
        * To inherit from this class
        * Overwrite the '_name' attribute
        * Overwrite the '_template' attribute with something of the form:
            {% macro header(this, kwargs) %}
                ...
            {% endmacro %}

            {% macro html(this, kwargs) %}
                ...
            {% endmacro %}

            {% macro script(this, kwargs) %}
                ...
            {% endmacro %}
    """
    def __init__(self):
        """TODO : docstring here"""
        super(MacroElement, self).__init__()
        self._name = 'MacroElement'

        self._template = Template(u"")

    def render(self, **kwargs):
        figure = self.get_root()
        assert isinstance(figure,Figure), ("You cannot render this Element "
            "if it's not in a Figure.")

        header = self._template.module.__dict__.get('header',None)
        if header is not None:
            figure.header.add_children(Element(header(self, kwargs)),
                                       name=self.get_name())

        html = self._template.module.__dict__.get('html',None)
        if html is not None:
            figure.html.add_children(Element(html(self, kwargs)),
                                       name=self.get_name())

        script = self._template.module.__dict__.get('script',None)
        if script is not None:
            figure.script.add_children(Element(script(self, kwargs)),
                                       name=self.get_name())

        for name, element in self._children.items():
            element.render(**kwargs)

def _parse_size(value):
    try:
        if isinstance(value, int) or isinstance(value, float):
            value_type = 'px'
            value = float(value)
            assert value > 0
        else:
            value_type = '%'
            value = float(value.strip('%'))
            assert 0 <= value <= 100
    except:
        msg = "Cannot parse value {!r} as {!r}".format
        raise ValueError(msg(value, value_type))
    return value, value_type

class Map(MacroElement):
    def __init__(self, location=None, width='100%', height='100%',
                 left="0%", top="0%", position='relative',
                 tiles='OpenStreetMap', API_key=None, max_zoom=18, min_zoom=1,
                 zoom_start=10, attr=None, min_lat=-90, max_lat=90,
                 min_lon=-180, max_lon=180):
        """Create a Map with Folium and Leaflet.js

        Generate a base map of given width and height with either default
        tilesets or a custom tileset URL. The following tilesets are built-in
        to Folium. Pass any of the following to the "tiles" keyword:
            - "OpenStreetMap"
            - "MapQuest Open"
            - "MapQuest Open Aerial"
            - "Mapbox Bright" (Limited levels of zoom for free tiles)
            - "Mapbox Control Room" (Limited levels of zoom for free tiles)
            - "Stamen" (Terrain, Toner, and Watercolor)
            - "Cloudmade" (Must pass API key)
            - "Mapbox" (Must pass API key)
            - "CartoDB" (positron and dark_matter)
        You can pass a custom tileset to Folium by passing a Leaflet-style
        URL to the tiles parameter:
        http://{s}.yourtiles.com/{z}/{x}/{y}.png

        Parameters
        ----------
        location: tuple or list, default None
            Latitude and Longitude of Map (Northing, Easting).
        width: pixel int or percentage string (default: '100%')
            Width of the map.
        height: pixel int or percentage string (default: '100%')
            Height of the map.
        tiles: str, default 'OpenStreetMap'
            Map tileset to use. Can use defaults or pass a custom URL.
        API_key: str, default None
            API key for Cloudmade or Mapbox tiles.
        max_zoom: int, default 18
            Maximum zoom depth for the map.
        zoom_start: int, default 10
            Initial zoom level for the map.
        attr: string, default None
            Map tile attribution; only required if passing custom tile URL.

        Returns
        -------
        Folium Map Object

        Examples
        --------
        >>>map = folium.Map(location=[45.523, -122.675], width=750, height=500)
        >>>map = folium.Map(location=[45.523, -122.675],
                            tiles='Mapbox Control Room')
        >>>map = folium.Map(location=(45.523, -122.675), max_zoom=20,
                            tiles='Cloudmade', API_key='YourKey')
        >>>map = folium.Map(location=[45.523, -122.675], zoom_start=2,
                            tiles=('http://{s}.tiles.mapbox.com/v3/'
                                    'mapbox.control-room/{z}/{x}/{y}.png'),
                            attr='Mapbox attribution')

        """
        super(Map, self).__init__()
        self._name = 'Map'

        if not location:
            # If location is not passed, we center the map at 0,0 and ignore zoom
            self.location = [0, 0]
            self.zoom_start = min_zoom
        else:
            self.location = location
            self.zoom_start = zoom_start

        # Map Size Parameters.
        self.width  = _parse_size(width)
        self.height = _parse_size(height)
        self.left = _parse_size(left)
        self.top  = _parse_size(top)
        self.position = position

        self.min_lat = min_lat
        self.max_lat = max_lat
        self.min_lon = min_lon
        self.max_lon = max_lon

        self.add_tile_layer(tiles=tiles, min_zoom=min_zoom, max_zoom=max_zoom,
                            attr=attr, API_key=API_key)

        self._template = Template(u"""
        {% macro header(this, kwargs) %}
            <style> #{{this.get_name()}} {
                position : {{this.position}};
                width : {{this.width[0]}}{{this.width[1]}};
                height: {{this.height[0]}}{{this.height[1]}};
                left: {{this.left[0]}}{{this.left[1]}};
                top: {{this.top[0]}}{{this.top[1]}};
            </style>
        {% endmacro %}
        {% macro html(this, kwargs) %}
            <div class="folium-map" id="{{this.get_name()}}" ></div>
        {% endmacro %}

        {% macro script(this, kwargs) %}

            var southWest = L.latLng({{ this.min_lat }}, {{ this.min_lon }});
            var northEast = L.latLng({{ this.max_lat }}, {{ this.max_lon }});
            var bounds = L.latLngBounds(southWest, northEast);

            var {{this.get_name()}} = L.map('{{this.get_name()}}', {
                                           center:[{{this.location[0]}},{{this.location[1]}}],
                                           zoom: {{this.zoom_start}},
                                           maxBounds: bounds,
                                           layers: []
                                         });
        {% endmacro %}
        """)

    def _repr_html_(self, figsize=(17,10), **kwargs):
        """Displays the Map in a Jupyter notebook.

        Parameters
        ----------
            self : folium.Map object
                The map you want to display

            figsize : tuple of length 2, default (17,10)
                The size of the output you expect in inches.
                Output is 60dpi so that the output has same size as a
                matplotlib figure with the same figsize.

        """
        if self._parent is None:
            self.add_to(Figure())
            out = self._parent._repr_html_(figsize=figsize, **kwargs)
            self._parent = None
        else:
            out = self._parent._repr_html_(figsize=figsize, **kwargs)
        return out

    def add_tile_layer(self, tiles='OpenStreetMap', name=None,
                       API_key=None, max_zoom=18, min_zoom=1,
                       attr=None, tile_name=None, tile_url=None,
                       active=False, **kwargs):
        if tile_name is not None:
            name = tile_name
            warnings.warn("'tile_name' is deprecated. Please use 'name' instead.")
        if tile_url is not None:
            tiles = tile_url
            warnings.warn("'tile_url' is deprecated. Please use 'tiles' instead.")

        tile_layer = TileLayer(tiles=tiles, name=name,
                               min_zoom=min_zoom, max_zoom=max_zoom,
                               attr=attr, API_key=API_key)
        self.add_children(tile_layer, name=tile_layer.tile_name)

class TileLayer(MacroElement):
    def __init__(self, tiles='OpenStreetMap', name=None,
                 min_zoom=1, max_zoom=18, attr=None, API_key=None):
        """TODO docstring here
        Parameters
        ----------
        """
        super(TileLayer, self).__init__()
        self._name = 'TileLayer'
        self.tile_name = name if name is not None else ''.join(tiles.lower().strip().split())

        self.min_zoom = min_zoom
        self.max_zoom = max_zoom

        self.tiles = ''.join(tiles.lower().strip().split())
        if self.tiles in ('cloudmade', 'mapbox') and not API_key:
            raise ValueError('You must pass an API key if using Cloudmade'
                             ' or non-default Mapbox tiles.')
        templates = list(self._env.list_templates(filter_func=lambda x: x.startswith('tiles/')))
        tile_template = 'tiles/'+self.tiles+'/tiles.txt'
        attr_template = 'tiles/'+self.tiles+'/attr.txt'

        if tile_template in templates and attr_template in templates:
            self.tiles = self._env.get_template(tile_template).render(API_key=API_key)
            self.attr  = self._env.get_template(attr_template).render()
        else:
            self.tiles = tiles
            if not attr:
                raise ValueError('Custom tiles must'
                                 ' also be passed an attribution')
            self.attr = attr

        self._template = Template(u"""
        {% macro script(this, kwargs) %}
            var {{this.get_name()}} = L.tileLayer(
                '{{this.tiles}}',
                {
                    maxZoom: {{this.max_zoom}},
                    minZoom: {{this.min_zoom}},
                    attribution: '{{this.attr}}'
                    }
                ).addTo({{this._parent.get_name()}});

        {% endmacro %}
        """)

class WmsTileLayer(TileLayer):
    def __init__(self, url, name=None,
                 format=None, layers=None, transparent=True,
                attribution=None):
        """TODO docstring here
        Parameters
        ----------
        """
        super(TileLayer, self).__init__()
        self._name = 'WmsTileLayer'
        self.tile_name = name if name is not None else 'WmsTileLayer_'+self._id
        self.url = url
        self.format = format
        self.layers = layers
        self.transparent = transparent
        #if attribution is None:
        #    raise ValueError('WMS must'
        #                     ' also be passed an attribution')
        self.attribution = attribution

        self._template = Template(u"""
        {% macro script(this, kwargs) %}
            var {{this.get_name()}} = L.tileLayer.wms(
                '{{ this.url }}',
                {
                    format:'{{ this.format }}',
                    transparent: {{ this.transparent.__str__().lower() }},
                    layers:'{{ this.layers }}',
                    attribution:'{{this.attribution}}'
                    }
                ).addTo({{this._parent.get_name()}});

        {% endmacro %}
        """)

class Icon(MacroElement):
    def __init__(self, color='blue', icon='info-sign', angle=0):
        """TODO : docstring here"""
        super(Icon, self).__init__()
        self._name = 'Icon'
        self.color = color
        self.icon = icon
        self.angle = angle

        self._template = Template(u"""
            {% macro script(this, kwargs) %}

                var {{this.get_name()}} = L.AwesomeMarkers.icon({
                    icon: '{{this.icon}}',
                    markerColor: '{{this.color}}',
                    prefix: 'glyphicon',
                    extraClasses: 'fa-rotate-{{this.angle}}'
                    });
                {{this._parent.get_name()}}.setIcon({{this.get_name()}});
            {% endmacro %}
            """)

class Marker(MacroElement):
    def __init__(self, location, popup=None, icon=None):
        """Create a simple stock Leaflet marker on the map, with optional
        popup text or Vincent visualization.

        Parameters
        ----------
        location: tuple or list, default None
            Latitude and Longitude of Marker (Northing, Easting)
        popup: string or tuple, default 'Pop Text'
            Input text or visualization for object. Can pass either text,
            or a tuple of the form (Vincent object, 'vis_path.json')
            It is possible to adjust the width of text/HTML popups
            using the optional keywords `popup_width` (default is 300px).
        icon: Icon plugin
            the Icon plugin to use to render the marker.

        Returns
        -------
        Marker names and HTML in obj.template_vars

        Example
        -------
        >>>map.simple_marker(location=[45.5, -122.3], popup='Portland, OR')
        >>>map.simple_marker(location=[45.5, -122.3], popup=(vis, 'vis.json'))

        """
        super(Marker, self).__init__()
        self._name = 'Marker'
        self.location = location

        self._template = Template(u"""
            {% macro script(this, kwargs) %}

            var {{this.get_name()}} = L.marker(
                [{{this.location[0]}},{{this.location[1]}}],
                {
                    icon: new L.Icon.Default()
                    }
                )
                .addTo({{this._parent.get_name()}});
            {% endmacro %}
            """)

class RegularPolygonMarker(MacroElement):
    def __init__(self, location, popup=None, icon=None,
                 color='black', opacity=1, weight=2,
                 fill_color='blue', fill_opacity=1,
                 number_of_sides=4, rotation=0, radius=15):
        """TODO : docstring here"""
        super(RegularPolygonMarker, self).__init__()
        self._name = 'RegularPolygonMarker'
        self.location = location
        self.icon = "new L.Icon.Default()" if icon is None else icon
        self.color   = color
        self.opacity = opacity
        self.weight  = weight
        self.fill_color  = fill_color
        self.fill_opacity= fill_opacity
        self.number_of_sides= number_of_sides
        self.rotation = rotation
        self.radius = radius

        self._template = Template(u"""
            {% macro script(this, kwargs) %}
            var {{this.get_name()}} = new L.RegularPolygonMarker(
                new L.LatLng({{this.location[0]}},{{this.location[1]}}),
                {
                    icon : new L.Icon.Default(),
                    color: '{{this.color}}',
                    opacity: {{this.opacity}},
                    weight: {{this.weight}},
                    fillColor: '{{this.fill_color}}',
                    fillOpacity: {{this.fill_opacity}},
                    numberOfSides: {{this.number_of_sides}},
                    rotation: {{this.rotation}},
                    radius: {{this.radius}}
                    }
                )
                .addTo({{this._parent.get_name()}});
            {% endmacro %}
            """)
    def render(self, **kwargs):
        super(RegularPolygonMarker, self).render()

        figure = self.get_root()
        assert isinstance(figure,Figure), ("You cannot render this Element "
            "if it's not in a Figure.")

        figure.header.add_children(\
            JavascriptLink("https://cdnjs.cloudflare.com/ajax/libs/leaflet-dvf"
                           "/0.2/leaflet-dvf.markers.min.js"),
            name='dvf_js')

class Html(Element):
    def __init__(self, data, width="100%", height="100%"):
        """TODO : docstring here"""
        super(Html, self).__init__()
        self._name = 'Html'
        self.data = data

        self.width  = _parse_size(width)
        self.height  = _parse_size(height)

        self._template = Template(u"""
        <div id="{{this.get_name()}}"
                style="width: {{this.width[0]}}{{this.width[1]}}; height: {{this.height[0]}}{{this.height[1]}};">
                {{this.data}}</div>
                """)

class Popup(Element):
    def __init__(self, html, max_width=300):
        super(Popup, self).__init__()
        self._name = 'Popup'
        self.header = Element()
        self.html   = Element()
        self.script = Element()

        self.header._parent = self
        self.html._parent = self
        self.script._parent = self

        if isinstance(html, Element):
            self.html.add_children(html)
        elif isinstance(html, text_type) or isinstance(html,binary_type):
            self.html.add_children(Html(text_type(html)))

        self.max_width = max_width

        self._template = Template(u"""
            var {{this.get_name()}} = L.popup({maxWidth: '{{this.max_width}}'});

            {% for name, element in this.html._children.items() %}
                var {{name}} = $('{{element.render(**kwargs).replace('\\n',' ')}}')[0];
                {{this.get_name()}}.setContent({{name}});
            {% endfor %}

            {{this._parent.get_name()}}.bindPopup({{this.get_name()}});

            {% for name, element in this.script._children.items() %}
                {{element.render()}}
            {% endfor %}
        """)

    def render(self, **kwargs):
        """TODO : docstring here."""
        for name, child in self._children.items():
            child.render(**kwargs)

        figure = self.get_root()
        assert isinstance(figure,Figure), ("You cannot render this Element "
            "if it's not in a Figure.")

        figure.script.add_children(Element(\
            self._template.render(this=self, kwargs=kwargs)), name=self.get_name())

class Vega(Element):
    def __init__(self, data, width='100%', height='100%',
                 left="0%", top="0%", position='relative'):
        """TODO : docstring here"""
        super(Vega, self).__init__()
        self._name = 'Vega'
        self.data = data

        # Size Parameters.
        self.width  = _parse_size(width)
        self.height = _parse_size(height)
        self.left = _parse_size(left)
        self.top  = _parse_size(top)
        self.position = position


        self._template = Template(u"")
    def render(self, **kwargs):
        self.json = json.dumps(self.data)

        self._parent.html.add_children(Element(Template("""
            <div id="{{this.get_name()}}"
                style="width: {{this.width[0]}}{{this.width[1]}}; height: {{this.height[0]}}{{this.height[1]}};">
                </div>
            """).render(this=self, kwargs=kwargs)), name=self.get_name())

        self._parent.script.add_children(Element(Template("""
            vega_parse({{this.json}},{{this.get_name()}});
            """).render(this=self)), name=self.get_name())

        figure = self.get_root()
        assert isinstance(figure,Figure), ("You cannot render this Element "
            "if it's not in a Figure.")

        figure.header.add_children(Element(Template("""
            <style> #{{this.get_name()}} {
                position : {{this.position}};
                width : {{this.width[0]}}{{this.width[1]}};
                height: {{this.height[0]}}{{this.height[1]}};
                left: {{this.left[0]}}{{this.left[1]}};
                top: {{this.top[0]}}{{this.top[1]}};
            </style>
            """).render(this=self, **kwargs)), name=self.get_name())

        figure.header.add_children(\
            JavascriptLink("https://cdnjs.cloudflare.com/ajax/libs/d3/3.5.5/d3.min.js"),
            name='d3')

        figure.header.add_children(\
            JavascriptLink("https://cdnjs.cloudflare.com/ajax/libs/vega/1.4.3/vega.min.js"),
            name='vega')

        figure.header.add_children(\
            JavascriptLink("https://code.jquery.com/jquery-2.1.0.min.js"),
            name='jquery')

        figure.script.add_children(\
            Template("""function vega_parse(spec, div) {
            vg.parse.spec(spec, function(chart) { chart({el:div}).update(); });}"""),
            name='vega_parse')

class GeoJson(MacroElement):
    def __init__(self, data):
        """Creates a GeoJson plugin to append into a map with
        Map.add_plugin.

        Parameters
        ----------
            data: file, dict or str.
                The geo-json data you want to plot.
                If file, then data will be read in the file and fully embeded in Leaflet's javascript.
                If dict, then data will be converted to json and embeded in the javascript.
                If str, then data will be passed to the javascript as-is.

                examples :
                    # providing file
                    GeoJson(open('foo.json'))

                    # providing dict
                    GeoJson(json.load(open('foo.json')))

                    # providing string
                    GeoJson(open('foo.json').read())
        """
        super(GeoJson, self).__init__()
        self._name = 'GeoJson'
        if 'read' in dir(data):
            self.data = data.read()
        elif type(data) is dict:
            self.data = json.dumps(data)
        else:
            self.data = data

        self._template = Template(u"""
            {% macro script(this, kwargs) %}
                var {{this.get_name()}} = L.geoJson({{this.data}}).addTo({{this._parent.get_name()}});
            {% endmacro %}
            """)

class GeoJsonStyle(MacroElement):
    def __init__(self, color_domain, color_code, color_data=None, key_on='feature.properties.color'):
        """TODO : docstring here.
        """
        super(GeoJsonStyle, self).__init__()
        self._name = 'GeoJsonStyle'

        self.color_domain = color_domain
        self.color_range = color_brewer(color_code, n=len(color_domain))
        self.color_data = json.dumps(color_data)
        self.key_on = key_on

        self._template = Template(u"""
            {% macro script(this, kwargs) %}
                var {{this.get_name()}} = {
                    color_scale : d3.scale.threshold()
                          .domain({{this.color_domain}})
                          .range({{this.color_range}}),
                    color_data : {{this.color_data}},
                    color_function : function(feature) {
                        {% if this.color_data=='null' %}
                            return this.color_scale({{this.key_on}});
                        {% else %}
                            return this.color_scale(this.color_data[{{this.key_on}}]);
                        {% endif %}
                        },
                    };

                {{this._parent.get_name()}}.setStyle(function(feature) {
                    return {
                        fillColor: {{this.get_name()}}.color_function(feature),
                        weight: 2,
                        opacity: 1,
                        color: 'white',
                        dashArray: '3',
                        fillOpacity: 0.7
                        };
                    });
            {% endmacro %}
            """)
    def render(self,**kwargs):
        super(GeoJsonStyle,self).render(**kwargs)

        figure = self.get_root()
        assert isinstance(figure,Figure), ("You cannot render this Element "
            "if it's not in a Figure.")

        figure.header.add_children(\
            JavascriptLink("https://cdnjs.cloudflare.com/ajax/libs/d3/3.5.5/d3.min.js"),
                                   name='d3')

class MarkerCluster(MacroElement):
    """Adds a MarkerCluster layer on the map."""
    def __init__(self):
        """Creates a MarkerCluster element to append into a map with
        Map.add_children.

        Parameters
        ----------
        """
        super(MarkerCluster, self).__init__()
        self._name = 'MarkerCluster'
        self._template = Template(u"""
            {% macro script(this, kwargs) %}
            var {{this.get_name()}} = L.markerClusterGroup();
            {{this._parent.get_name()}}.addLayer({{this.get_name()}});
            {% endmacro %}
            """)
    def render(self, **kwargs):
        super(MarkerCluster, self).render()

        figure = self.get_root()
        assert isinstance(figure,Figure), ("You cannot render this Element "
            "if it's not in a Figure.")
        figure.header.add_children(\
            JavascriptLink("https://cdnjs.cloudflare.com/ajax/libs/leaflet.markercluster"
                           "/0.4.0/leaflet.markercluster-src.js"),
            name='marker_cluster_src')

        figure.header.add_children(\
            JavascriptLink("https://cdnjs.cloudflare.com/ajax/libs/leaflet.markercluster"
                           "/0.4.0/leaflet.markercluster.js"),
            name='marker_cluster')

        figure.header.add_children(\
            CssLink("https://cdnjs.cloudflare.com/ajax/libs/leaflet.markercluster/0.4.0/MarkerCluster.css"),
            name='marker_cluster_css')

        figure.header.add_children(\
            CssLink("https://cdnjs.cloudflare.com/ajax/libs/leaflet.markercluster/0.4.0/MarkerCluster.Default.css"),
            name="marker_cluster_default_css")

/*jslint browser: true, nomen: true, indent: 4, maxlen: 80 */
/*global window, jQuery, _, Ext  */

var mapstory = mapstory || {};

(function ($) {
    'use strict';
    var LayerResult, LayerSearch, layerElementTemplate, widgetTemplate;


    layerElementTemplate = new Ext.Template(
        '<div class="ms-layer-title">',
        '<p>',
        '<a class="show-meta" href="#">{title}</a> by ',
        '<a href="<%= layer.owner_detail %>">{owner}</a> on ',
        '{last_modified} ',
        '<a class="ms-add-to-map" href="#">Add to map</a>',
        '</p>',
        '</div>',
        '<div class="ms-layer-info">',
        '<img src="{thumb}">',
        '<p class="ms-layer-rating">{views} Views |',
        ' {rating} Rating</p>',
        '<div class="ms-layer-abstract">{abstract}</div>',
        '</div>'

    ).compile();

    // maybe this template should live in the html document
    widgetTemplate = new Ext.Template(
    '<div id="ms-header">',
      '<form>',
        '<fieldset>',
          '<button id="search" type="submit">Search</button>',
          '<input id="query" type="text" class="search-query">',
          '<select id="sortBy">',
            '<option value="newest">Newest</option>',
            '<option value="oldest">Oldest</option>',
            '<option value="alphaaz">Alphabetical (A-Z)</option>',
            '<option value="alphaza">Alphabetical (Z-A)</option>',
            '<option value="popularity">Popularity</option>',
            '<option value="rel">Relevance</option>',
          '</select>',
        '</fieldset>',
        '<fieldset>',
          '<label>Show meta info expanded</label>',
          '<input id="show-meta-info" type="checkbox" checked>',
        '<button id="prev">Prev</button>',
        '<button id="next">Next</button>',
        '</fieldset>',
      '</form>',
    '</div>',
    '<div id="ms-search-layers">',
      '<ul>',
      '</ul>',
    '</div>',
    '<div id="ms-footer">',
      '<button id="done">Done</button>',
    '</div>').compile();

    LayerResult = function (options) {
        this.$el = $('<li>');
        this.layer = options.layer;
        this.geoExplorer = options.geoExplorer;
        this.template = layerElementTemplate;
    };

    LayerResult.prototype.checkLayerSource = function (callback) {
        var ge = this.geoExplorer,
            layer = this.layer,
            sourceId = layer.name + '-search',
                    // get the layer source from Geo explorer
            source = ge.layerSources[sourceId];

        if (!source) {
            source = ge.addLayerSource({
                id: sourceId,
                config: {
                    isLazy: function () { return false; },
                    ptype: 'gxp_wmscsource',
                    hidden: true,
                    restUrl: "/gs/rest", // TODO hard coded
                    version: "1.1.1",
                    url: layer.owsUrl
                }
            });
            source.on({
                ready: function () {
                    callback(source);
                }
            });
        } else {
            callback(source);
        }

    };

    LayerResult.prototype.addToMap = function () {

        var ge = this.geoExplorer,
            layerStore = ge.mapPanel.layers,
            layer = this.layer;

        this.checkLayerSource(function (source) {
            var record = source.createLayerRecord({
                name: layer.name.split(':').pop(),
                source: source.id
            });

            layerStore.add(record);

        });
    };

    LayerResult.prototype.toggleInfo = function (event) {
        this.$el.find('div.ms-layer-info').toggle();
    };

    LayerResult.prototype.render = function (showMeta) {

        this.$el.html(this.template.apply(this.layer));


        if (!showMeta) {
            this.$el.find('div.ms-layer-info').hide();
        }


        this.$el.find('.ms-layer-abstract').expander({
            collapseTimer: 0,
            slicePoint: 200
        });


        this.$el.find('a.ms-add-to-map').click(this.addToMap.bind(this));

        this.$el.find('.show-meta').click(this.toggleInfo.bind(this));

        return this;
    };

    // main view object controls rendering widget template and
    // controls the events that are attached to this widget
    LayerSearch = function (options) {

        this.searchUrl = options.searchUrl;
        this.geoExplorer = options.geoExplorer;

        this.pageSize = options.pageSize || 10;

        this.currentPage = 1;
        this.numberOfRecords = 0;

        this.$el = $('<div/>', {
            id: 'ms-search-widget'
        });

        $(window).resize(this.setLeft.bind(this));

        this.setLeft();
        this.template = widgetTemplate;

    };

    LayerSearch.prototype.setPageButtons = function () {
        this.setPrevButton();
        this.setNextButton();
    };


    LayerSearch.prototype.setPrevButton = function () {
        if (this.currentPage < 2) {
            this.$el.find('#prev').attr('disabled', '');
        } else {
            this.$el.find('#prev').removeAttr('disabled');
        }

    };
    LayerSearch.prototype.setNextButton = function () {
        var button = this.$el.find('#next'),
            currentLoc = this.currentPage * this.pageSize;

        if (currentLoc >= this.numberOfRecords && this.numberOfRecords !== 0) {
            this.$el.find('#next').attr('disabled', '');
        } else {
            this.$el.find('#next').removeAttr('disabled');
        }
    };

    LayerSearch.prototype.getStart = function () {
        return this.pageSize * this.currentPage - this.pageSize;
    };

    LayerSearch.prototype.setLeft = function () {
        var widgetWidth = 600;
        this.$el.css('left', $(window).width() / 2 - widgetWidth / 2);
    };

    LayerSearch.prototype.renderLayer = function (layer) {
        var element = new LayerResult({
                layer: layer,
                geoExplorer: this.geoExplorer
            }).render(this.showMeta);

        this.$layerList.append(element.$el);
    };

    LayerSearch.prototype.renderLayers = function (layers) {
        var self = this;
        this.numberOfRecords = layers.total;

         // if the start location is higher than the number of
        // returned records, then reset the page number and redo the
        // query
        if (layers.total <= this.getStart() && layers.total !== 0) {
            this.currentPage = 1;
            this.doSearch();
        }
        this.$layerList.empty();
        this.setPageButtons();
        $.each(layers.rows, function (idx, layer) {
            self.renderLayer(layer);
        });

    };

    LayerSearch.prototype.doSearch = function () {
        this.showMeta = this.$el.find(
            '#show-meta-info:checkbox'
        ).is(':checked');

        var queryParameters = {
                // hard code the type as it does not make sense to add a
                // map to another map
                bytype: 'layer',
                limit: this.pageSize,
                start: this.getStart(),
                sort: this.$el.find('#sortBy').val()
            },
            q  = this.$el.find('#query').val();

        if (q !== '') {
            queryParameters.q = q;
        }

        $.ajax({
            url: this.searchUrl,
            data: queryParameters
        }).done(this.renderLayers.bind(this));


    };


    LayerSearch.prototype.render = function () {
        var doSearch = this.doSearch.bind(this);

        this.$el.append(this.template.apply());
        this.$layerList = this.$el.find('#ms-search-layers ul');

        // populate the widget when its rendered
        this.doSearch();

        // after the elements are added to the dom element attach the
        // events
        this.$el.find('#done').click(
            function () {
                this.$el.remove();
            }.bind(this)
        );

        this.$el.find('#search').click(doSearch);
        this.$el.find('#sortBy').change(doSearch);
        this.$el.find('#bbox-limit').change(doSearch);
        this.$el.find('#show-meta-info').change(doSearch);
        this.$el.find('form').keypress(function (evt) {
            // prevent the default event on the return key and redo
            // the query
            if (evt.which === 13) {
                evt.preventDefault();
                doSearch();
            }

        });
        // TODO, these seem very similar see how to combine them
        this.$el.find('#prev').click(function (event) {
            event.preventDefault();
            this.currentPage = this.currentPage - 1;
            this.setPageButtons();
            this.doSearch();
        }.bind(this));

        this.$el.find('#next').click(function (event) {
            event.preventDefault();
            this.currentPage = this.currentPage + 1;
            this.setPageButtons();
            this.doSearch();
        }.bind(this));

        this.setPageButtons();
        $('body').append(this.$el);
        return this;
    };

    window.mapstory.LayerSearch = LayerSearch;

}(jQuery));

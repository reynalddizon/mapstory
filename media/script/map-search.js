/*jslint browser: true, nomen: true, indent: 4*/
/*global window, jQuery, Ext, OpenLayers  */

// include this for older versions of ie, ie8 i am looking at you.
// find a better place for this
// taken from the mdn
// https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Function/bind?redirectlocale=en-US&redirectslug=JavaScript%2FReference%2FGlobal_Objects%2FFunction%2Fbind#Compatibility
if (!Function.prototype.bind) {
    Function.prototype.bind = function (oThis) {
        'use strict';

        if (typeof this !== "function") {
            throw new TypeError(
                "What is trying to be bound is not callable"
            );
        }

        var slice = Array.prototype.slice,
            aArgs = slice.call(arguments, 1),
            fToBind = this,
            FNOP = function () {},
            fBound = function () {
                return fToBind.apply(
                    this instanceof FNOP && oThis
                        ? this
                        : oThis,
                    aArgs.concat(slice.call(arguments))
                );
            };

        FNOP.prototype = this.prototype;
        fBound.prototype = new FNOP();

        return fBound;
    };
}


(function ($) {
    'use strict';
    var LayerResult,
        LayerSearch,
        layerElementTemplate,
        widgetTemplate,
        View,
        TestView;

    Ext.ns('mapstory');

    layerElementTemplate = new Ext.Template(
        '<div class="ms-layer-title">',
        '<p>',
        '<a title="Add this storylayer to the mapstory" class="ms-title" href="#">{title}</a> by ',
        '<a href="{owner_detail}">{owner}</a> on ',
        '{last_modified} ',
        '<a class="show-meta" href="#">Less</a>',
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
        '<div class="x-tool x-tool-close"> </div>',
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
        '<label>Show expanded</label>',
        '<input id="show-meta-info" type="checkbox" checked>',
        '</fieldset>',
        '<fieldset>',
        '<label>Limit search to map extent</label>',
        '<input id="current-extent" type="checkbox">',
        '</fieldset>',
        '<fieldset>',
        '<label>Limit search to current time range</label>',
        '<input id="current-time" disabled type="checkbox">',
        '</fieldset>',
        '<fieldset>',
        '<button id="prev">Prev</button>',
        '<button id="next">Next</button>',
        '<span id="total"></span>',
        '</fieldset>',
        '</form>',
        '</div>',
        '<div id="ms-search-layers">',
        '<ul>',
        '</ul>',
        '</div>',
        '<div id="ms-footer">',
        '<button id="done">Done</button>',
        '</div>'
    ).compile();


    LayerResult = function (options) {
        this.$el = $('<li/>');
        this.layer = options.layer;
        this.geoExplorer = options.geoExplorer;
        this.template = layerElementTemplate;

        this.$el.on(
            'click',
            'a.ms-title, .ms-layer-info img',
            this.addToMap.bind(this)
        );
        this.$el.on(
            'click',
            '.show-meta',
            this.toggleInfo.bind(this)
        );

    };

    LayerResult.prototype = {
        constructor: LayerResult,

        checkLayerSource: function (callback) {
            var ge = this.geoExplorer,
                self = this,
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
                        callback.call(self, source);
                    }
                });
            } else {
                callback.call(self, source);
            }

        },

        addToMap: function () {
            var ge = this.geoExplorer,
                layerStore = ge.mapPanel.layers,
                layer = this.layer;

            this.checkLayerSource(function (source) {
                var record = source.createLayerRecord({
                    name: layer.name.split(':').pop(),
                    source: source.id
                });
                if (record) {
                    layerStore.add(record);
                    this.zoomToLayer(record);
                }
            });

        },

        zoomToLayer: function (record) {
            var layer  = record.getLayer(),
                extent = layer.maxExtent;
            this.geoExplorer.mapPanel.map.zoomToExtent(extent);
        },

        setMetaButton: function (state) {
            var button = this.$el.find('a.show-meta');
            button.html(state);
            return this;
        },

        toggleInfo: function (evt) {
            // kind of messy, Figure out a better way of doing this
            var oldState = this.$el.find('a.show-meta').html(),
                state;

            if (oldState === 'More') {
                state = 'Less';
            } else {
                state = 'More';
            }
            this.setMetaButton(state);
            this.$el.find('div.ms-layer-info').toggle();
        },

        render: function (showMeta) {
            this.$el.html(this.template.apply(this.layer));

            if (!showMeta) {
                this.$el.find('div.ms-layer-info').hide();
                // we hide the meta data we need to make sure we
                // handle the state correctly
                this.setMetaButton('More');
            }

            this.$el.find('.ms-layer-abstract').expander({
                collapseTimer: 0,
                slicePoint: 200
            });

            return this;
        }

    };


    // make these functions so we can pass them as arguments to
    // another function
    function inc(x) {
        return x + 1;
    }

    function dec(x) {
        return x - 1;
    }

    // main view object controls rendering widget template and
    // controls the events that are attached to this widget
    LayerSearch = function (options) {

        this.searchUrl = options.searchUrl;
        this.geoExplorer = options.geoExplorer;
        this.map = options.map || null;
        this.pageSize = options.pageSize || 25;
        this.currentPage = 1;
        this.numberOfRecords = 0;
        this.timeEndable = false;

        // all of a mock to be used instead of hard coding the jquery
        // ajax method
        this.httpFactory = options.httpFactory || $.ajax;
        this.template = widgetTemplate;
        this.$el = $('<div/>', {
            id: 'ms-search-widget'
        });

        $(window).resize(this.adjustWidget.bind(this));
        // handle all of the events for the ui, these are all attached
        // using event delegation so they can be bound before the
        // child dom element is inserted into the dom
        var doSearch = this.doSearch.bind(this);
        this.$el.on('click', '#done', this.close.bind(this));
        this.$el.on('click', '#search', doSearch);
        this.$el.on('change', '#sortBy', doSearch);
        // all inputs are covered by the following selector
        // #show-meta-info
        // #current-extent
        // #current-time
        this.$el.on('change', 'input', doSearch);
        this.$el.on('click', '#prev', this.handlePage.bind(this, dec));
        this.$el.on('click', '#next', this.handlePage.bind(this, inc));
        this.$el.on('submit', 'form', function (evt) {
            evt.preventDefault();
            doSearch();
        });


        this.isTimeEnabled();
        this.findTimeControl();
    };


    LayerSearch.prototype = {
        constructor: LayerSearch,

        /** Wait until all of the tools/controls have been populated and
         *  then grab a reference to the playback tool
         */
        isTimeEnabled: function () {
            this.geoExplorer.on('ready', function () {
                this.map = this.geoExplorer.mapPanel.map;
                this.findTimeControl();
                this.map.events.on({
                    'addlayer': this.isTimeLayer,
                    scope: this
                });
                this.map.events.on({moveend: this.doSearch, scope: this});
            }, this);

        },
        /** Checks if a layer has a time metadata object attached to
         *  it. Sets the value of this.timeEndable to be true if so
         *  @param {event}
         */
        isTimeLayer: function (evt) {
            var layer = evt.layer;

            if (layer.metadata && layer.metadata.timeInfo) {
                this.timeEnable = true;
                this.findTimeControl();
                this.enableTimeFilter();
            }
        },

        findTimeControl: function () {
            if (this.map) {

                this.map.controls.forEach(function (control) {
                    if (control instanceof OpenLayers.Control.DimensionManager) {
                        this.timeEnable = true;
                        if (!this.timeControle) {
                            this.timeControl = control;
                        }

                    }
                }, this);
            }
        },

        enableTimeFilter: function () {
            if (this.timeEnable) {
                this.$el.find('#current-time').removeAttr('disabled');
            }

        },

        handlePage: function (opt, evt) {
            evt.preventDefault();
            this.setPageButtons();
            this.currentPage = opt(this.currentPage);
            this.doSearch();
        },

        adjustWidget: function () {
            // FIXME these are all hard coded
            var widgetWidth = 600;
            this.$el.css('left', $(window).width() / 2 - widgetWidth / 2);
            this.$el.find('#ms-search-layers ul').css(
                'max-height',
                $(window).height() - 300
            );
        },
        setPageButtons: function () {
            this.setPrevButton();
            this.setNextButton();
        },

        setPrevButton: function () {
            if (this.currentPage < 2) {
                this.$el.find('#prev').attr('disabled', '');
            } else {
                this.$el.find('#prev').removeAttr('disabled');
            }
        },

        setNextButton: function () {
            var button = this.$el.find('#next'),
                currentLoc = this.currentPage * this.pageSize;

            if (currentLoc >= this.numberOfRecords && this.numberOfRecords !== 0) {
                this.$el.find('#next').attr('disabled', '');
            } else if (this.numberOfRecords === 0) {
                // handle case where there are 0 results
                this.$el.find('#next').attr('disabled', '');
            } else {
                this.$el.find('#next').removeAttr('disabled');
            }

        },

        getStart: function () {
            return this.pageSize * this.currentPage - this.pageSize;
        },

        renderLayer: function (layer) {
            var element = new LayerResult({
                layer: layer,
                geoExplorer: this.geoExplorer
            }).render(this.showMeta);

            this.$layerList.append(element.$el);
        },

        renderTotal: function () {
            var numberOfDisplayed = 0,
                isLastPage = (this.currentPage * this.pageSize) > this.numberOfRecords;

            if (isLastPage) {
                numberOfDisplayed = this.numberOfRecords - (this.currentPage - 1) * this.pageSize;
            } else {
                numberOfDisplayed = this.pageSize;
            }


            this.$el.find('#total').html(
                'Displaying ' + numberOfDisplayed + ' of ' + this.numberOfRecords
            );
        },

        renderLayers: function (data) {
            this.numberOfRecords = data.total;
            this.renderTotal();
            // if the start location is higher than the number of
            // returned records, then reset the page number and redo the
            // query
            if (data.total <= this.getStart() && data.total !== 0) {
                this.currentPage = 1;
                this.doSearch();
            }

            if (data.total === 0) {
                this.currentPage = 1;
            }

            this.$layerList.empty();
            this.setPageButtons();

            var self = this;
            $.each(data.rows, function (idx, layer) {
                self.renderLayer(layer);
            });

        },

        // search the current bounding box
        // min_x,min_y,max_x,max_y
        doSearchExtent: function (query, searchExtentP) {
            var extent;
            if (searchExtentP) {
                // it seems like the only safe way to access the map
                // object is via this path.
                // TODO, find a way to save a reference to the map
                // object
                extent = this.geoExplorer.mapPanel.map.getExtent().transform(
                    this.geoExplorer.mapPanel.map.getProjection(),
                    "EPSG:4326"
                );

                query.byextent = extent.toArray().join(',');
            }
            return query;
        },

        formatDate: function (date) {
            date = new Date(date);
            return date.getFullYear() + '-' + date.getMonth() + '-' + date.getDate();
        },

        // search api uses byperiod
        doSearchTime: function (query, searchTimeP) {
            var time, range, start, end;
            if (searchTimeP) {
                range = this.timeControl.animationRange;
                start = this.formatDate(range[0]);
                end   = this.formatDate(range[1]);
                query.byperiod = encodeURI([start, end]);
            }
            return query;
        },

        doSearch: function () {

            this.showMeta = this.$el.find(
                '#show-meta-info:checkbox'
            ).is(':checked');

            var searchExtent = this.$el.find('#current-extent').is(':checked'),
                searchTime   = this.$el.find('#current-time').is(':checked'),
                extent,
                range,
                queryParameters = {
                    // hard code the type as it does not make sense to add a
                    // map to another map
                    bytype: 'layer',
                    limit: this.pageSize,
                    start: this.getStart(),
                    sort: this.$el.find('#sortBy').val()
                },
                q  = this.$el.find('#query').val();

            this.doSearchExtent(queryParameters, searchExtent);
            this.doSearchTime(queryParameters, searchTime);

            if (q) {
                queryParameters.q = q;
            }

            this.httpFactory({
                url: this.searchUrl,
                data: queryParameters,
                success: this.renderLayers.bind(this)
            });

        },

        render: function () {
            var hover = function() { $(this).toggleClass('x-tool-close-over'); };
            this.$el.append(this.template.apply());
            this.$el.find('.x-tool-close').hover(hover, hover).
                    click(this.close.bind(this));
            this.enableTimeFilter();
            this.$layerList = this.$el.find('#ms-search-layers ul');
            this.adjustWidget();
            // populate the widget when its rendered
            this.doSearch();
            this.setPageButtons();
            $('body').append(this.$el);
            return this;
        },

        close: function() {
            // jquery's remove should also remove all of the events
            // attached to this element and its children
            // http://api.jquery.com/remove/
            this.$el.remove();
        }

    };


    window.mapstory.LayerSearch = LayerSearch;

}(jQuery));

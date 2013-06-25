function installHitCount(callback) {
    Ext.onReady(function() {
        var tracker = false;
        function checkload() {
            var i, control;
            if (tracker) return;
            for (i in app.mapPanel.map.controls) {
                control = app.mapPanel.map.controls[i];
                if (control.CLASS_NAME == "OpenLayers.Control.DimensionManager") {
                    tracker = function(ev) {
                        callback();
                        control.events.unregister('tick', null, tracker);
                    }
                    control.events.register('tick', null, tracker);
                    return;
                }
            }
        }
        function listen() {
            app.mapPanel.map.events.register("addlayer", null, function(ev) {
                ev.layer.events.register("loadend", null, function(ev) {
                    checkload();
                });
            });
        }
        if (app.mapPanel) {
            listen();
        } else {
            app.on("portalready", listen);
        }
    });
}
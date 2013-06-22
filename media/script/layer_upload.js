function setup(options) {
    Ext.onReady(function() {
        init(options);
    });
}
function init(options) {
    Ext.QuickTips.init();
    options = Ext.apply({
        is_featuretype : true,
        layer_name : null
    },options);

    var xml_unsafe = /(^[^a-zA-Z\._]+)|([^a-zA-Z0-9\._])/g;

    var zipFileNames = [];

    var listeners = {
        "fileselected": function(cmp, value) {
            // remove the path from the filename - avoids C:/fakepath etc.
            cmp.setValue(value.split(/[/\\]/).pop());
        }
    };
    var form_fields = [{
            xtype: "hidden",
            name: "csrfmiddlewaretoken",
            value: options.csrf_token
        }];

    var base_file = new Ext.ux.form.FileUploadField({
        id: 'base_file',
        emptyText: gettext('Select a layer data file'),
        fieldLabel: gettext('Data'),
        name: 'base_file',
        allowBlank: false,
        listeners: listeners,
        validator: function(name) {
            return isMainFile(name) && name.length <= 64;
        }
    });

    var dbf_file = new Ext.ux.form.FileUploadField({
        id: 'dbf_file',
        emptyText: gettext('Select a .dbf data file'),
        fieldLabel: gettext('DBF'),
        name: 'dbf_file',
        allowBlank: true,
        listeners: listeners,
        validator: function(name) {
            if ((name.length > 0) && (name.search(/\.dbf$/i) == -1)) {
                return gettext("Invalid DBF File.");
            } else {
                return true;
            }
        }
    });

    var shx_file = new Ext.ux.form.FileUploadField({
        id: 'shx_file',
        emptyText: gettext('Select a .shx data file'),
        fieldLabel: gettext('SHX'),
        name: 'shx_file',
        allowBlank: true,
        listeners: listeners,
        validator: function(name) {
            if ((name.length > 0) && (name.search(/\.shx$/i) == -1)) {
                return gettext("Invalid SHX File.");
            } else {
                return true;
            }
        }
    });

    var prj_file = new Ext.ux.form.FileUploadField({
        id: 'prj_file',
        emptyText: gettext('Select a .prj data file (optional)'),
        fieldLabel: gettext('PRJ'),
        name: 'prj_file',
        allowBlank: true,
        listeners: listeners,
        validator: function(name) {
            if ((name.length > 0) && (name.search(/\.prj$/i) == -1)) {
                return gettext("Invalid PRJ File.");
            } else {
                return true;
            }
        }
    });

    var sld_file = new Ext.ux.form.FileUploadField({
        id: 'sld_file',
        emptyText: gettext('Select a .sld style file (optional)'),
        fieldLabel: gettext('SLD'),
        name: 'sld_file',
        allowBlank: true,
        listeners: listeners
    });

    var abstractField = new Ext.form.TextArea({
        id: 'abstract',
        fieldLabel: gettext('Abstract'),
        name: 'abstract',
        allowBlank: true
    });

    var permissionsField = new Ext.form.Hidden({
        name: "permissions"
    });
    
    function containerFromDom(id) {
        return new Ext.Container({
            contentEl : id
        });
    }
    
    var zipMsg = containerFromDom('zip-msg').hide();
    var shpMsg = containerFromDom('shp-msg').hide();
    var csvMsg = containerFromDom('csv-msg').hide();
    var rasterMsg = containerFromDom('raster-msg').hide();
    var unknownMsg = containerFromDom('unknown-msg').hide();
    var tooLongMsg = containerFromDom('too-long-msg').hide();

    form_fields.push(base_file);
    form_fields.push(zipMsg);
    form_fields.push(shpMsg);
    form_fields.push(csvMsg);
    form_fields.push(rasterMsg);
    form_fields.push(unknownMsg);
    form_fields.push(tooLongMsg);
    form_fields.push(sld_file);
    
    if (options.is_featuretype) {
        form_fields = form_fields.concat(dbf_file, shx_file, prj_file);
    }
    
    form_fields.push(containerFromDom('notes'));
    form_fields.push(containerFromDom('about-data'));
    
    if (!options.layer_name) {
        form_fields = form_fields.concat(permissionsField);
    }
    
    function errorHandler(fp, o) {
        var html = '', msgs = Ext.get('form-messages');
        if (o.result === false) {
            html = o.response.responseText;
        } else {
            for (var i = 0; i < o.result.errors.length; i++) {
                html += '<li>' + o.result.errors[i] + '</li>';
            }
        }
        msgs.query('ul')[0].innerHTML = html;
        msgs.slideIn('t');
    }

    var fp = new Ext.FormPanel({
        renderTo: 'upload_form',
        fileUpload: true,
        width: 600,
        frame: true,
        autoHeight: true,
        unstyled: true,
        labelWidth: 50,
        defaults: {
            anchor: '95%',
            msgTarget: 'side'
        },
        items: form_fields,
        monitorValid: true,
        monitorPoll: 500,
        listeners: {
            clientvalidation: function(form, valid) {
                checkFormValid();
            }
        },
        buttons: [{
            text: gettext('Upload'),
            handler: function(){
                fp.submitted = true;
                if (checkFormValid(true)) {
                    fp.getForm().submit({
                        url: options.form_target,
                        waitMsg: gettext('Uploading your data...'),
                        success: function(fp, o) {
                            document.location = o.result.redirect_to;
                        },
                        failure: errorHandler
                    });
                }
            }
        }]
    });

    var disable_shapefile_inputs = function() {
        dbf_file.hide();
        shx_file.hide();
        prj_file.hide();
    };

    var enable_shapefile_inputs = function() {
        dbf_file.show();
        shx_file.show();
        prj_file.show();
    };

    var showFileMessage = function(ext, iszip) {
        shpMsg.hide();
        csvMsg.hide();
        zipMsg.hide();
        rasterMsg.hide();
        unknownMsg.hide();
        if (ext == null) return;
        tooLongMsg.hide();
        Ext.get("zip-msg-container").addClass('hide');
        if (base_file.getValue().length > 64) {
            tooLongMsg.show();
            checkFormValid();
            return;
        }
        if (ext == null) return;
        switch (ext) {
            case 'shp':
                // if the shp is in a zip, don't show the message
                if (! iszip) {
                    shpMsg.show();
                }
                break;
            case 'csv':
                csvMsg.show();
                break;
            case 'zip':
                zipMsg.show();
                break;
            case 'tif':
            case 'tiff':
            case 'geotiff':
            case 'png':
            case 'jpg':
                rasterMsg.show();
                break;
            default:
                unknownMsg.show();
        }
    };

    var checkFileType = function() {
        var ext = getExtension(base_file.getValue());
        if (ext == 'shp') {
            enable_shapefile_inputs();
        } else {
            disable_shapefile_inputs();
        }
        checkFormValid();
        if (test_file_api()) {
            if ('base_file' in dropped_files) {
                file = dropped_files['base_file'];
            } else {
                file = Ext.get('base_file-file').dom.files[0];
            }
            if (file == null || !checkZipContent(file, null)) {
                showFileMessage(ext, false);
            }
        } else {
            showFileMessage(ext, false);
        }
    };
    
    function checkFormValid(notify) {
        if (! fp.submitted) return false;
        var validation = Ext.get('form-validation'), valid = fp.getForm().isValid();
        if ( valid ) {
            validation.enableDisplayMode().hide();
        } else {
            if (!validation.isVisible()) {
                validation.slideIn('t');
            } else if (notify == true) {
                validation.frame();
            }
        }
        return valid;
    }

    base_file.addListener('fileselected', function(cmp, value) {
        checkFileType();
    });
    
    if (options.layer_name) {
        enable_shapefile_inputs();
    } else {
        disable_shapefile_inputs();
    }

    if (! options.layer_name) {
        var permissionsEditor = new GeoNode.PermissionsEditor({
            renderTo: "permissions_form",
            userLookup: options.userLookup,
            listeners: {
                updated: function(pe) {
                    permissionsField.setValue(Ext.util.JSON.encode(pe.writePermissions()));
                }
            },
            permissions: {
                anonymous: 'layer_readonly',
                authenticated: 'layer_readonly',
                users:[]
            }
        });
        permissionsEditor.fireEvent("updated", permissionsEditor);
    }

    function test_file_api() {
        var fi = document.createElement('INPUT');
        fi.type = 'file';
        return 'files' in fi;
    }
    
    function getExtension(name) {
        var parts = name.split('.');
        return parts[parts.length - 1];
    }
    
    function isMainFile(name) {
        var ext = getExtension(name);
        return /^(zip)$/i.test(ext) || isVectorExt(ext) || isRasterExt(ext);
    }
    
    function isVectorExt(ext) {
        return /^(csv|shp)$/i.test(ext);
    }

    function isRasterExt(ext) {
        return /^(tif|tiff|geotiff|png|jpg)$/i.test(ext);
    }
    
    function isShapefileComponent(ext) {
        return /^(shp|dbf|prj|shx)$/.text(ext);
    }

    function checkZipContent(file) {
        var directoryPresent = false, success = true, 
            vectorMainFile = null, rasterMainFile = null;
        if (! /\.zip$/.test(file.name)) return false;

        function complete(msg, ext) {
            var msgContainer = Ext.get("zip-msg-container");
            if (msg) {
                msgContainer.select('div').addClass('hide');
                msgContainer.select(msg).removeClass('hide');
                msgContainer.removeClass('hide');
            }
            if (ext) {
                msgContainer.addClass('hide');
                showFileMessage(ext, true);
            }
            Ext.get('show-files').removeClass('hide');
        }

        function skipFile(zipEntry) {
            return zipEntry.filename.indexOf('__MACOSX') >= 0; // yay
        }

        zip.createReader(new zip.BlobReader(file), function(reader) {
            // get all entries from the zip
            reader.getEntries(function(entries) {
                var i, e, ext, main;
                zipFileNames = [];
                for (i = 0; i < entries.length; i++) {
                    if (!skipFile(entries[i])) {
                        zipFileNames.push(entries[i].filename);
                    }
                }
                for (i = 0; i < entries.length; i++) {
                    e = entries[i];

                    if (skipFile(e)) continue;
                    
                    if (e.directory) {
                        directoryPresent = true;
                    }
                    ext = getExtension(e.filename);
                    if (isVectorExt(ext)) {
                        if (rasterMainFile || vectorMainFile) {
                            return complete('#single-file', null);
                        }
                        vectorMainFile = e.filename;
                    }
                    if (isRasterExt(ext)) {
                        if (vectorMainFile) {
                            return complete('#single-file', null);
                        }
                        rasterMainFile = e.filename;
                    }
                }
                
                if (directoryPresent) {
                    return complete('#no-directories', null);
                }

                if (!rasterMainFile && !vectorMainFile) {
                    return complete('#no-recognized', null);
                }

                main = rasterMainFile == null ? vectorMainFile : rasterMainFile;

                return complete(null, getExtension(main));
            });
        }, function(error) {
            complete('#error-reading', false);
        });
        return true;
    }

    if (test_file_api()) {
        // track dropped files separately from values of input fields
        var dropped_files = {};
        // drop handler
        var drop = function(ev) {
            ev.preventDefault();
            var dt = ev.dataTransfer, files = dt.files, i = 0, ext, key, w, notRecognized = [];
            for (; i < files.length; i++) {
                ext = getExtension(files[i].name);
                if (isMainFile(ext)) {
                    base_file.setValue(files[i].name);
                    dropped_files.base_file = files[i];
                } else {
                    try {
                        key = ext + '_file', w = eval(key);
                        w.setValue(files[i].name);
                        dropped_files[key] = files[i];
                    } catch (ReferenceError) {
                        notRecognized.push(files[i].name);
                    }
                }
            }
            checkFileType();
            if (notRecognized.length) {
                notRecognized.splice(0, 0, "These files are not recognized:");
                errorHandler(null, {result : { errors : notRecognized}});
            } else {
                Ext.get('form-messages').enableDisplayMode().hide();
            }
        };

        var dropTarget = Ext.get("drop-target");
        function t() {
            dropTarget.toggleClass('drop-hover');
        }
        Ext.get("drop-target").addListener("dragover", function(ev) {
            ev.stopPropagation();
            ev.preventDefault();
        }).addListener("drop", function(ev) {
            dropTarget.removeClass('drop-hover');
            drop(ev.browserEvent);
        }).addListener("dragexit",t).addListener("dragenter",t).setStyle('display','block');
        
        function createDragFormData() {
            var data = new FormData(), id, value, fields = fp.getForm().getFieldValues(), size = 0;
            for (id in fields) {
                value = fields[id];
                if (id in dropped_files) {
                    size = size + dropped_files[id].size;
                    data.append(id,dropped_files[id],value);
                } else {
                    data.append(id,value);
                }
            }
            return data;
        }

        function upload(formData) {
            var xhr = new XMLHttpRequest();
            var progress;

            xhr.upload.addEventListener('loadstart', function(ev) {
                progress = Ext.MessageBox.progress("Please wait","Uploading your data...");
            }, false);
            xhr.upload.addEventListener('progress', function(ev) {
                if (ev.lengthComputable) {
                    // assume that 25% of the time will be actual server work, not just upload time
                    var msg = parseInt(ev.loaded / 1024) + " of " + parseInt(ev.total / 1024);
                    progress.updateProgress( (ev.loaded/ev.total)* .75, msg);
                    if (ev.loaded == ev.total) {
                        progress.updateProgress(.75,"Awaiting response");
                    }
                }
            }, false);

            function error(ev,result) {
                var error_message;
                if (typeof result == 'undefined') {
                    result = ["Unexpected Error: " + xhr.responseText];
                }
                progress.hide();
                errorHandler(ev, {result:result});
            }
            xhr.addEventListener('load', function(ev) {
                try {
                    var result = Ext.decode(xhr.responseText);
                    if (result.success) {
                        document.location = result.redirect_to;
                    } else {
                        error(ev, result);
                    }
                } catch (ex) {
                    error(ev);
                    console.log(ex);
                }
            }, false);
            xhr.addEventListener('error', error, false);

            xhr.open("POST",options.form_target, true);
            xhr.setRequestHeader('X-Requested-With', 'XMLHttpRequest');
            xhr.send(formData);
        }

        var originalHandler = fp.buttons[0].handler;
        fp.buttons[0].handler = function() {
            var file;
            fp.submitted = true;
            if (!checkFormValid(true)) return;

            if ('base_file' in dropped_files) {
                upload(createDragFormData());
            } else {
                originalHandler();
            }
        };

        Ext.get('show-files').on('click', function() {
            var els = [], el, i, list = Ext.get('file-list'), name;
            for (i=0; i < zipFileNames.length; i++) {
                name = zipFileNames[i]
                el = { tag: 'li', html: name };
                if (!/\.zip$/i.test(name) && isMainFile(name)) {
                    el['class'] = 'bitchin';
                    el['style'] = { 'font-weight': 'bold'};
                }
                els.push(el);
            }
            Ext.DomHelper.overwrite(list, {
                tag : 'ul',
                children: els
            });
            list.removeClass('hide');
        });
    }
    
    var confirmDelete = true;
    var activeDelete = null;
    function deleteUpload(el) {
        var a = new Ext.Element(el);
        Ext.Ajax.request({
            url : a.getAttribute('href'),
            success : function() {
                var uip = a.parent('.uip');
                Ext.get('confirm-delete').hide().appendTo(uip.parent());
                uip.remove();
                if (Ext.select('.uip').getCount() == 0) {
                    Ext.get('no-uip').removeClass('hide').fadeIn();
                }
            },
            failure : function() {
                alert('Uh oh. An error occurred.')
            }
        });
        Ext.get('confirm-delete').hide();
    }
    Ext.select('#confirm-delete a').on('click',function(ev) {
        var resp = Ext.get(this).getAttribute('href');
        ev.preventDefault();
        if (/n/.test(resp)) {
            Ext.get('confirm-delete').hide();
        } else {
            if (/yy/.test(resp)) {
                confirmDelete = false;
            }
            deleteUpload(activeDelete);
        }
        
    });
    Ext.select('.uip .icon-trash').on('click',function(ev) {
        ev.preventDefault();
        if (confirmDelete) {
            activeDelete = this;
            Ext.get('confirm-delete').removeClass('hide').appendTo(Ext.get(this).parent('.uip')).enableDisplayMode().show();
        } else {
            deleteUpload(this);
        }
    });
}

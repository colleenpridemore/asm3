/*jslint browser: true, forin: true, eqeq: true, white: true, sloppy: true, vars: true, nomen: true */
/*global $, jQuery, _, asm, common, config, controller, dlgfx, format, header, html, tableform, validate */

$(function() {

    var dialog = {
        add_title: _("New template"),
        helper_text: _("Template names can include a path portion with /, eg: Vets/Rabies Certificate"),
        close_on_ok: true,
        columns: 1,
        width: 550,
        fields: [
            { post_field: "template", label: _("Template Name"), validation: "notblank", type: "text" }
        ]
    };

    var table = {
        rows: controller.rows,
        idcolumn: "ID",
        edit: function(row) {
            window.location = "document_edit?template=" + row.ID;
        },
        columns: [
            { field: "NAME", display: _("Template") },
            { field: "PATH", display: _("Path"), initialsort: true }
        ]
    };

    var buttons = [
         { id: "new", text: _("New"), icon: "document", tooltip: _("Create a new template"), enabled: "always", 
             click: function() { 
                 tableform.dialog_show_add(dialog, function() {
                     tableform.fields_post(dialog.fields, "mode=create", "document_templates", function(response) {
                         window.location="document_edit?template=" + response;
                     });
                 });
             } 
         },
         { id: "newodt", text: _("Upload ODT"), icon: "media-add", tooltip: _("Upload a new OpenOffice template"), enabled: "always", 
             hideif: function() { 
                 return !config.bool("AllowODTDocumentTemplates");
             },
             click: function() { 
                 $("#dialog-newodt").dialog("open");
             } 
         },
         { id: "clone", text: _("Clone"), icon: "copy", tooltip: _("Create a new template by copying the selected template"), enabled: "one", 
             click: function() { 
                 var ids = tableform.table_ids(table);
                 tableform.dialog_show_add(dialog, function() {
                     tableform.fields_post(dialog.fields, "mode=clone&ids=" + ids , "document_templates", function(response) {
                         window.location="document_edit?template=" + response;
                     });
                 });
             } 
         },
         { id: "delete", text: _("Delete"), icon: "delete", enabled: "multi", 
             click: function() { 
                 tableform.delete_dialog(function() {
                     tableform.buttons_default_state(buttons);
                     var ids = tableform.table_ids(table);
                     common.ajax_post("document_templates", "mode=delete&ids=" + ids , function() {
                         tableform.table_remove_selected_from_json(table, controller.rows);
                         tableform.table_update(table);
                     });
                 });
             } 
         },
         { id: "rename", text: _("Rename"), icon: "link", enabled: "one", 
             click: function() { 
                 $("#newname").val(tableform.table_selected_row(table).NAME);
                 $("#dialog-rename").dialog("open");
             } 
         }

    ];

    var document_templates = {
        render_rename_dialog: function() {
            return [
                '<div id="dialog-rename" style="display: none" title="' + html.title(_("Rename")) + '">',
                '<table width="100%">',
                '<tr>',
                '<td><label for="newname">' + _("New name") + '</label></td>',
                '<td><input id="newname" data="newname" type="textbox" class="asm-textbox" /></td>',
                '</tr>',
                '</table>',
                '</div>'
            ].join("\n");
        },

        bind_rename_dialog: function() {
            var renamebuttons = { };
            renamebuttons[_("Rename")] = function() {
                $("#dialog-rename label").removeClass("ui-state-error-text");
                if (!validate.notblank([ "newname" ])) { return; }
                $("#dialog-rename").disable_dialog_buttons();
                var dbfsid = tableform.table_ids(table).split(",")[0];
                var newname = encodeURIComponent($("#newname").val());
                common.ajax_post("document_templates", "mode=rename&newname=" + newname + "&dbfsid=" + dbfsid , function() {
                    window.location = "document_templates";
                });
            };
            renamebuttons[_("Cancel")] = function() {
                $("#dialog-rename").dialog("close");
            };
            $("#dialog-rename").dialog({
                autoOpen: false,
                width: 550,
                modal: true,
                dialogClass: "dialogshadow",
                show: dlgfx.edit_show,
                hide: dlgfx.edit_hide,
                buttons: renamebuttons
            });
        },

        render_newodt_dialog: function() {
            return [
                '<div id="dialog-newodt" style="display: none" title="' + html.title(_("Upload a new OpenOffice template")) + '">',
                '<form id="form-newodt" action="document_templates" method="post" enctype="multipart/form-data">',
                '<input type="hidden" name="mode" value="createodt" />',
                '<table width="100%">',
                '<tr>',
                '<td><label for="filechooser">' + _("Document file") + '</label></td>',
                '<td><input id="filechooser" name="filechooser" type="file" /></td>',
                '</tr>',
                '<tr>',
                '<td><label for="odtpath">' + _("Path") + '</label></td>',
                '<td><input id="odtpath" name="path" type="textbox" class="asm-textbox" /></td>',
                '</tr>',
                '</table>',
                '</form>',
                '</div>'
            ].join("\n");
        },

        bind_newodt_dialog: function() {
            var odtbuttons = { };
            odtbuttons[_("Upload")] = function() {
                $("#dialog-newodt label").removeClass("ui-state-error-text");
                if (!validate.notblank([ "filechooser" ])) { return; }
                $("#dialog-newodt").disable_dialog_buttons();
                $("#form-newodt").submit();
            };
            odtbuttons[_("Cancel")] = function() {
                $("#dialog-newodt").dialog("close");
            };
            $("#dialog-newodt").dialog({
                autoOpen: false,
                width: 550,
                modal: true,
                dialogClass: "dialogshadow",
                show: dlgfx.edit_show,
                hide: dlgfx.edit_hide,
                buttons: odtbuttons
            });
        },

        render: function() {
            var s = "";
            s += this.render_rename_dialog();
            s += this.render_newodt_dialog();
            s += tableform.dialog_render(dialog);
            s += html.content_header(_("Document Templates"));
            s += tableform.buttons_render(buttons);
            s += tableform.table_render(table);
            s += html.content_footer();
            return s;
        },

        bind: function() {
            tableform.dialog_bind(dialog);
            tableform.buttons_bind(buttons);
            tableform.table_bind(table, buttons);
            this.bind_rename_dialog();
            this.bind_newodt_dialog();
        }

    };

    common.module(document_templates, "document_templates", "options");

});
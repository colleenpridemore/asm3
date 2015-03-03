/*jslint browser: true, forin: true, eqeq: true, white: true, sloppy: true, vars: true, nomen: true */
/*global $, jQuery, _, asm, common, config, controller, dlgfx, format, header, html, validate */

$(function() {

    var person_find = {

        render: function() {
            return [
                html.content_header(_("Find Person")),
                '<form id="personsearchform" action="person_find_results" method="GET">',
                '<p class="asm-search-selector">',
                '<a id="asm-search-selector-simple" href="#">' + _("Simple") + '</a> |',
                '<a id="asm-search-selector-advanced" href="#">' + _("Advanced") + '</a>',
                '</p>',
                '<div id="asm-criteria-simple">',
                '<table class="asm-table-layout">',
                '<tr>',
                '<td>',
                '<label for="q">' + _("Search") + '</label>',
                '</td>',
                '<td>',
                '<input id="mode" data="mode" type="hidden" value="SIMPLE" />',
                '<input id="q" data="q" class="asm-textbox" />',
                '</td>',
                '</tr>',
                '</table>',
                '</div>',
                '<div id="asm-criteria-advanced">',
                '<table class="asm-table-layout">',
                '<tr>',
                '<td>',
                '<label for="code">' + _("Code contains") + '</label>',
                '</td>',
                '<td>',
                '<input id="code" data="code" class="asm-textbox" />',
                '</td>',
                '</tr>',
                '<tr>',
                '<td>',
                '<label for="name">' + _("Name contains") + '</label>',
                '</td>',
                '<td>',
                '<input id="name" data="name" class="asm-textbox" />',
                '</td>',
                '<td>',
                '<label for="address">' + _("Address contains") + '</label>',
                '</td>',
                '<td>',
                '<input id="address" data="address" class="asm-textbox" />',
                '</td>',
                '</tr>',
                '<tr id="towncountyrow">',
                '<td>',
                '<label for="town">' + _("City contains") + '</label>',
                '</td>',
                '<td>',
                '<input id="town" data="town" class="asm-textbox" />',
                '</td>',
                '<td>',
                '<label for="county">' + _("State contains") + '</label>',
                '</td>',
                '<td>',
                '<input id="county" data="county" class="asm-textbox" />',
                '</td>',
                '</tr>',
                '<tr>',
                '<td>',
                '<label for="postcode">' + _("Zipcode contains") + '</label>',
                '</td>',
                '<td>',
                '<input id="postcode" data="postcode" class="asm-textbox" />',
                '</td>',
                '<td>',
                '<label for="homecheck">' + _("Homecheck areas") + '</label>',
                '</td>',
                '<td>',
                '<input id="homecheck" data="homecheck" class="asm-textbox" />',
                '</td>',
                '</tr>',
                '<tr>',
                '<td>',
                '<label for="comments">' + _("Comments contain") + '</label>',
                '</td>',
                '<td>',
                '<input id="comments" data="comments" class="asm-textbox" />',
                '</td>',
                '<td>',
                '<label for="email">' + _("Email") + '</label>',
                '</td>',
                '<td>',
                '<input id="email" data="email" class="asm-textbox" />',
                '</td>',
                '</tr>',
                '<tr>',
                '<td>',
                '<label for="medianotes">' + _("Media notes contain") + '</label>',
                '</td>',
                '<td>',
                '<input id="medianotes" data="medianotes" class="asm-textbox" />',
                '</td>',
                '<td>',
                '<label for="filter">' + _("Show") + '</label>',
                '</td>',
                '<td>',
                '<select id="filter" data="filter" multiple="multiple" class="asm-bsmselect">',
                '</select>',
                '</td>',
                '</tr>',
                '</table>',
                '</div>',
                '<p class="centered">',
                '<button id="searchbutton" type="button">' + _("Search") + '</button>',
                '</p>',
                '</form>',
                html.content_footer()
            ].join("\n");
        },

        bind: function() {
            // Switch to simple search criteria
            var simpleMode = function() {
                $("#mode").val("SIMPLE");
                $("#asm-search-selector-advanced").removeClass("asm-link-disabled");
                $("#asm-search-selector-simple").addClass("asm-link-disabled");
                $("#asm-criteria-advanced").slideUp(function() {
                    $("#asm-criteria-simple").slideDown(function() {
                        $("input[data='q']").focus();
                    });
                });
            };

            // Switch to advanced search criteria
            var advancedMode = function() {
                $("#mode").val("ADVANCED");
                $("input[data='q']").val("");
                $("#asm-search-selector-simple").removeClass("asm-link-disabled");
                $("#asm-search-selector-advanced").addClass("asm-link-disabled");
                $("#asm-criteria-simple").slideUp(function() {
                    $("#asm-criteria-advanced").slideDown(function() {
                        $("input[data='name']").focus();
                    });
                });
            };

            // Handle switching between modes via the links
            $("#asm-search-selector-simple").click(function() {
                simpleMode();
            });

            $("#asm-search-selector-advanced").click(function() {
                advancedMode();
            });

            // Load the person flag options
            html.person_flag_options(null, controller.flags, $("#filter"), true);

            // Search button - we don't use the traditional submit because
            // the bsmselect widget craps extra values into the form and 
            // breaks filtering by flag
            $("#searchbutton").button().click(function() {
                window.location = "person_find_results?" + $("#personsearchform input, #personsearchform select").toPOST();
            });

            // We need to re-enable the return key submitting the form
            $("#personsearchform").keypress(function(e) {
                if (e.keyCode == 13) {
                    window.location = "person_find_results?" + $("#personsearchform input, #personsearchform select").toPOST();
                }
            });

            // Get the default mode and set that
            $("#asm-criteria-simple").hide();
            $("#asm-criteria-advanced").hide();
            if (config.bool("AdvancedFindOwner")) {
                advancedMode();
            }
            else {
                simpleMode();
            }
        }
    };

    common.module(person_find, "person_find", "criteria");

});
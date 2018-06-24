$( function() {
  $.widget( "custom.combobox", {
    _create: function() {
      this.wrapper = $( "<span>" )
        .addClass( "custom-combobox" )
        .insertAfter( this.element );

      this.element.hide();
      this._createAutocomplete();
      this._createShowAllButton();
    },

    _createAutocomplete: function() {
      var selected = this.element.children( ":selected" ),
        value = selected.val() ? selected.text() : "";

      this.input = $( "<input>" )
        .appendTo( this.wrapper )
        .val( value )
        .attr( "title", "" )
        .addClass( "custom-combobox-input ui-widget ui-widget-content ui-state-default ui-corner-left" )
        .autocomplete({
          delay: 0,
          minLength: 0,
          source: $.proxy( this, "_source" )
        })
        .tooltip({
          classes: {
            "ui-tooltip": "ui-state-highlight"
          }
        });

      this._on( this.input, {
        autocompleteselect: function( event, ui ) {
          ui.item.option.selected = true;
          this._trigger( "select", event, {
            item: ui.item.option
          });
        },

        autocompletechange: "_removeIfInvalid"
      });
    },

    _createShowAllButton: function() {
      var input = this.input,
        wasOpen = false;

      $( "<a>" )
        .attr( "tabIndex", -1 )
        .appendTo( this.wrapper )
        .button({
          icons: {
            primary: "ui-icon-triangle-1-s"
          },
          text: false
        })
        .removeClass( "ui-corner-all" )
        .addClass( "custom-combobox-toggle ui-corner-right" )
        .on( "mousedown", function() {
          wasOpen = input.autocomplete( "widget" ).is( ":visible" );
        })
        .on( "click", function() {
          input.trigger( "focus" );

          // Close if already visible
          if ( wasOpen ) {
            return;
          }

          // Pass empty string as value to search for, displaying all results
          input.autocomplete( "search", "" );
        });
    },

    _source: function( request, response ) {
      var matcher = new RegExp( $.ui.autocomplete.escapeRegex(request.term), "i" );
      response( this.element.children( "option" ).map(function() {
        var text = $( this ).text();
        if ( this.value && ( !request.term || matcher.test(text) ) )
          return {
            label: text,
            value: text,
            option: this
          };
      }) );
    },

    _removeIfInvalid: function( event, ui ) {

      // Selected an item, nothing to do
      if ( ui.item ) {
        return;
      }

      // Search for a match (case-insensitive)
      var value = this.input.val(),
        valueLowerCase = value.toLowerCase(),
        valid = false;
      this.element.children( "option" ).each(function() {
        if ( $( this ).text().toLowerCase() === valueLowerCase ) {
          this.selected = valid = true;
          return false;
        }
      });

      // Found a match, nothing to do
      if ( valid ) {
        return;
      }

      // Remove invalid value
      this.input
        .val( "" )
        .attr( "title", "Aucun résultat pour « " + value + " »")
        .tooltip( "open" );
      this.element.val( "" );
      this._delay(function() {
        this.input.tooltip( "close" ).attr( "title", "" );
      }, 2500 );
      this.input.autocomplete( "instance" ).term = "";
    },

    _destroy: function() {
      this.wrapper.remove();
      this.element.show();
    }
  });

/*  $.widget("custom.pykol_formset", {
    _create: function() {
      formset_prefix = this.element.attr("data-formset-prefix");
      this.management_form_total = $("#id_" + formset_prefix + "-TOTAL_FORMS").val();
      this.management_form_min = $("#id_" + formset_prefix + "-MIN_NUM_FORMS").val();
      this.management_form_max = $("#id_" + formset_prefix + "-MAX_NUM_FORMS").val();
      this.management_form_initial = $("#id_" + formset_prefix + "-INITIAL_FORMS").val();

      var extra_forms = this.management_form_total - this.management_form_initial;

      for(var i = 0; i < extra_forms; i++) {
        this.element.find("tr").last().remove();
      }
      $("#id_" + formset_prefix + "-TOTAL_FORMS").val(this.management_form_initial);

      tr = $("<tr>").appendTo(this.element);
      td = $("<td>").appendTo(tr);
      link = $("<a>+ Ajouter une ligne</a>")
        .appendTo(td);
    },
  }); */
} );

// Bouton d'ajout de ligne dans un formset

$(document).ready(function() {
  $( ".formset select" ).combobox();
  $(".formset tbody tr").formset({
    addText: '<i class="fa fa-plus"></i> Ajouter un nouvel élément',
    deleteText: '<i class="fa fa-trash"></i> Supprimer',
  });
  // TODO: bug, les éléments ajoutés n'ont pas leur propre combobox mais
  // activent celui du dernier élément présent initialement dans le
  // formulaire.
  // TODO la suppression avec formset ne marche pas
});

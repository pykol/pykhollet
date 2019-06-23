/**
 * pyKol - Gestion de colles en CPGE
 * Copyright (c) 2019 Florian Hatat
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Affero General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Affero General Public License for more details.
 *
 * You should have received a copy of the GNU Affero General Public License
 * along with this program.  If not, see <https://www.gnu.org/licenses/>.
 */

/**
 * Interface de gestion des colles d'orales via un calendrier.
 */

/**
 * Classe pour accéder facilement aux données d'un formset Django.
 */
class ColleFormset {
  constructor(id, prefix) {
    this.formset_prefix = prefix;
    var formset_element = document.getElementById(id);
    this.formset_element = formset_element;

    this.formset = formset_element;
    // Hack pour contourner le tbody d'un tableau
    if(formset_element instanceof HTMLTableElement) {
      var tbody = formset_element.getElementsByTagName('tbody');
      if(tbody.length > 0) {
        this.formset = tbody[0];
      }
    }
    this.template = document.getElementById("template_" + id);
    this.management_total_forms =
      document.getElementById('id_' + this.formset_prefix +
        '-TOTAL_FORMS');
    this.management_max_forms = parseInt(
      document.getElementById('id_' + this.formset_prefix +
          '-MAX_NUM_FORMS').value, 10);
    this.lignes = new Object();
    this.ligne_next_id = 0;

    // Initialisation du tableau avec les lignes déjà existantes
    for(var ligne_html of this.formset.children) {
      this.lignes[this.newLigneId()] = ligne_html;
    }
  }

  getTotalForms() {
    return parseInt(this.management_total_forms.value, 10);
  }

  setTotalForms(val) {
    this.management_total_forms.value = val;
  }

  newLigneId() {
    var ligne_id = "ligne" + this.ligne_next_id;
    this.ligne_next_id++;
    return ligne_id;
  }

  // Construit le nom du champ input attendu par Django
  inputName(position, field) {
    return this.formset_prefix + "-" + position + "-" + field;
  }

  ajoutLigne(data) {
    // On teste si on a épuisé le nombre maximal de lignes permis
    // par Django.
    if(this.management_max_forms <= this.getTotalForms()) {
      return null;
    }

    var form_id = this.getTotalForms();
    var ligne_id = this.newLigneId();

    var ligne = document.importNode(this.template.content, true);
    var setField = (function(name, value) {
      var input = ligne.querySelector('[name="' + this.formset_prefix + "-__prefix__-" + name + '"]');
      input.value = value;
      input.name = this.inputName(form_id, name);
      input.id = 'id_' + input.name;
    }).bind(this);
    for(var cle in data) {
      if(data.hasOwnProperty(cle)) {
        setField(cle, data[cle]);
      }
    }
    ligne = this.formset.appendChild(ligne.children[0]);
    this.setTotalForms(this.getTotalForms() + 1);
    this.lignes[ligne_id] = ligne;
    return ligne_id;
  }

  // Renvoie la liste des données pour une ligne du formset, donnée par
  // son identifiant unique.
  ligneData(ligne_id) {
    var data = {};
    var ligne_html = this.lignes[ligne_id];
    var position = this.positionOf(ligne_html);
    var name_prefix = this.formset_prefix + "-" + position + "-";
    for(var item of this.lignes[ligne_id].querySelectorAll('*')) {
      if(item.hasAttribute('name') &&
        item.attributes['name'].value.startsWith(name_prefix)) {
        var key = item.attributes['name'].value.substring(name_prefix.length);
        data[key] = item.value;
      }
    }
    return data;
  }

  // Renvoie le tableau des données de toutes les lignes
  getAllData() {
    var data = new Array();
    for(var ligne_id in this.lignes) {
      if(this.lignes.hasOwnProperty(ligne_id)) {
        var ligne_data = this.ligneData(ligne_id);
        ligne_data.ligne_id = ligne_id;
        data.push(ligne_data);
      }
    }
    return data;
  }

  // Déterminer la position (index de l'enfant dans l'arbre DOM du
  // formset) de la ligne.
  positionOf(ligne_html) {
    for(var position = 0; position < this.getTotalForms(); position++) {
      if(this.formset.children[position] == ligne_html) {
        return position;
      }
    }
    return null;
  }

  // Supprimer une ligne du tableau
  supprimerLigne(ligne_id) {
    var ligne = this.lignes[ligne_id];
    var position = this.positionOf(ligne);

    // TODO vérifier que l'on ne passe pas en dessous de MIN_NUM_FORMS
    // Les lignes d'origine du formset ne doivent pas être retirées,
    // mais on coche le champ de suppression de Django.
    if(ligne.querySelector('[name="' + this.inputName(position, 'id') + '"]')) {
      var delete_box = ligne.querySelector('[name="' + this.inputName(position, 'DELETE') + '"]');
      delete_box.checked = true;
    }
    else {
      // On renumérote les lignes suivantes du formset
      var name_regexp = new RegExp('^(' + this.formset_prefix +
        '-)\\d+(-.*)' + '$');
      for(var element = ligne.nextElementSibling;
        element != null;
        position++, element = element.nextElementSibling) {
        for(var item of element.querySelectorAll('*')) {
          if(item.hasAttribute('name')) {
            item.attributes['name'].value =
              item.attributes['name'].value.replace(name_regexp,
                '$1' + position + '$2');
          }
        }
      }
      this.formset.removeChild(ligne);
      this.setTotalForms(this.getTotalForms() - 1);
    }
  }
}

document.addEventListener('DOMContentLoaded', function() {
  var calendarEl = document.createElement('div');
  var formset = new ColleFormset('calendrier_colleur_formset', 'form');

  formset.formset_element.parentNode.insertBefore(calendarEl,
    formset.formset_element);

  var duree_passage_defaut = document.getElementById('duree_passage_defaut');

  var calendar = new FullCalendar.Calendar(calendarEl, {
    plugins: [ 'timeGrid', 'interaction' ],
    defaultView: 'timeGridWeek',
    locale: 'fr',
    allDaySlot: false,
    minTime: "08:00:00",
    maxTime: "20:00:00",
    firstDay: 1,
    weekends: false,
    allDaySlot: false,
    height: 'auto',
    events: function(fetchInfo, successCallback, failureCallback) {
      var data = new Array();
      for(var ev of formset.getAllData()) {
        data.push({
          title: "Colle",
          id: ev.ligne_id,
          start: ev.debut,
          end: ev.fin,
        });
      }
      successCallback(data);
    },
    dateClick: function(info) {
      date_fin = new Date(info.date.getTime());
      date_fin.setHours(date_fin.getHours() + 1);
      var id = formset.ajoutLigne({
        debut: info.date.toISOString(),
        duree: 'PT1H',
        duree_etudiant: "PT" + duree_passage_defaut.value + "M",
      });

      if(id != null) {
        this.addEvent({
          title: "Nouvelle colle",
          id: id,
          start: info.date,
          end: date_fin,
        });
      }
    },
    eventRender: function(info) {
      var span = document.createElement("span");
      span.setAttribute('class', 'evenement_supprimer');
      span.setAttribute('title', "Supprimer la colle");
      span.textContent = "🗙";
      span.addEventListener('click', function() {
        info.event.remove();
        formset.supprimerLigne(info.event.id);
      });
      info.el.appendChild(span);
    }
  });

  /**
   * Gestion de l'ajout/suppression des colles déjà existantes dans le
   * formset lorsque l'on clique sur la case à cocher "supprimer".
   */
  function toggle_existing_line(ev) {
    var ligne_id;
    for(ligne_id in formset.lignes) {
      if(formset.lignes.hasOwnProperty(ligne_id)
        && formset.lignes[ligne_id].contains(ev.currentTarget)) {
        break;
      }
    }
    if(ev.currentTarget.checked) {
      calendar.getEventById(ligne_id).remove();
    }
    else {
      var ligne_data = formset.ligneData(ligne_id);
      calendar.addEvent({
        title: "Colle",
        id: ligne_id,
        start: ligne_data.debut,
        end: ligne_data.fin,
      });
    }
  }

  for(var delete_checkbox of
    formset.formset.querySelectorAll('[name$="-DELETE"][name^="' + formset.formset_prefix + '-"]')) {
    delete_checkbox.addEventListener('change', toggle_existing_line);
  }

  /* Affichage du calendrier. */
  calendar.render();
});

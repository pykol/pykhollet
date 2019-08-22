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
 * Outils pour gérer les formsets Django depuis le client.
 */
class DjangoFormset {
  constructor(formset_element) {
    // TODO guess prefix
    this.formset_prefix = ...;
    this.formset_element = formset_element;

    this.formset = formset_element;
    // Hack pour contourner le tbody d'un tableau
    if(formset_element instanceof HTMLTableElement) {
      var tbody = formset_element.getElementsByTagName('tbody');
      if(tbody.length > 0) {
        this.formset = tbody[0];
      }
    }

    this.template = formset_element.querySelector("template");

    this.management_total_forms =
      document.getElementById('id_' + this.formset_prefix +
        '-TOTAL_FORMS');
    this.management_min_forms = parseInt(
      document.getElementById('id_' + this.formset_prefix +
          '-MIN_NUM_FORMS').value, 10);
    this.management_max_forms = parseInt(
      document.getElementById('id_' + this.formset_prefix +
          '-MAX_NUM_FORMS').value, 10);

    // Objet qui à chaque identifiant unique de ligne associe son
    // fragment DOM.
    this.form_lines = new Object();
    this.next_line_id = 0;

    // Objet qui à chaque position dans l'arbre DOM associe
    // l'identifiant de la ligne.
    this.form_ids = new Array();

    // On garde trace du bouton d'ajout pour le désactiver si nécessaire
    this.add_button = null;

    // Initialisation du tableau avec les lignes déjà existantes
    for(var position = 0; position < this.formset.children.length; position++) {
      var line_id = this.newLineId();
      this.registerFormLine(this.newLineId(), this.formset.children[position], position);
    }
  }

  registerFormLine(line_id, html_content, form_id) {
    this.form_lines[line_id] = {
      'html_content': html_content,
      'form_id': form_id,
      'delete_button': null
    };
    this.form_ids[form_id] = line_id;
  }

  newLineId() {
    var line_id = "lineid-" + this.formset_prefix + "-" + this.next_line_id;
    this.next_line_id++;
    return line_id;
  }

  getTotalForms() {
    return parseInt(this.management_total_forms.value, 10);
  }

  setTotalForms(val) {
    this.management_total_forms.value = val;
  }

  canAdd() {
    return this.getTotalForms() < this.management_max_forms;
  }

  canDelete() {
    return this.getTotalForms() > this.management_min_forms;
  }

  // Construit le nom du champ <input> attendu par Django
  inputName(position, field) {
    return this.formset_prefix + "-" + position + "-" + field;
  }

  setData(line_id, data) {
    var html_line = this.lines[line_id].html_content;
    var form_id = this.lines[line_id].form_id;

    var setField = (function(name, value) {
      //TODO __prefix__
      var input = line.querySelector('[name="' + this.inputName(form_id, name) + '"]');
      input.value = value;
    }).bind(this);

    for(var key in data) {
      if(data.hasOwnProperty(key)) {
        setField(key, data[key]);
      }
    }
  }

  // Ajoute une ligne avec les données passées en paramètre. Cette
  // méthode renvoie l'identifiant de la nouvelle ligne.
  addLine() {
    // On teste si on a épuisé le nombre maximal de lignes permis
    // par Django.
    if(!this.candAdd()) {
      return null;
    }

    var form_id = this.getTotalForms();
    var line_id = this.newLineId();
    // TODO réattribuer proprement les attributs "name"
    var html_line = this.formset.appendChild(document.importNode(this.template.content, true).children[0]);
    for(var element of html_line.querySelectorAll(...)) {
      var name = ...;
      element.name = this.inputName(form_id, name);
      element.id = 'id_' + element.name;
    }
    this.setTotalForms(this.getTotalForms() + 1);
    this.registerFormLine(line_id, html_line, form_id);
    return line_id;
  }

  // Renvoie la liste des données pour une ligne du formset, donnée par
  // son identifiant unique.
  getData(line_id) {
    var data = {};
    var html_line = this.form_lines[line_id].html_content;
    var form_id = this.form_lines[line_id].form_id;
    var name_prefix = this.formset_prefix + "-" + form_id + "-";
    for(var item of this.html_lines[line_id].querySelectorAll('*')) {
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
    for(var line_id in this.form_lines) {
      if(this.form_lines.hasOwnProperty(line_id)) {
        var line_data = this.getData(line_id);
        line_data.line_id = line_id;
        data.push(line_data);
      }
    }
    return data;
  }

  // Déterminer la position (index de l'enfant dans l'arbre DOM du
  // formset) de la ligne.
  positionOf(html_line) {
    for(var position = 0; position < this.getTotalForms(); position++) {
      if(this.formset.children[position] == html_line) {
        return position;
      }
    }
    return null;
  }

  // Supprimer une ligne du tableau
  deleteLine(line_id) {
    var line = this.form_lines[line_id].html_content;
    var form_id = this.form_lines[line_id].form_id;
    delete this.form_lines[line_id];

    // On vérifie que l'on ne passe pas en dessous de MIN_NUM_FORMS
    if(!this.canDelete()) {
      return;
    }

    // Les lignes d'origine du formset ne doivent pas être retirées,
    // mais on coche le champ de suppression de Django.
    if(line.querySelector('[name="' + this.inputName(form_id, 'id') + '"]')) {
      var delete_box = line.querySelector('[name="' + this.inputName(form_id, 'DELETE') + '"]');
      delete_box.checked = true;
    }
    else {
      // On renumérote les lignes suivantes du formset
      var name_regexp = new RegExp('^(' + this.formset_prefix +
        '-)\\d+(-.*)' + '$');
      for(var element = line.nextElementSibling;
        element != null;
        form_id++, element = element.nextElementSibling) {
        for(var item of element.querySelectorAll('*')) {
          if(item.hasAttribute('name')) {
            item.attributes['name'].value =
              item.attributes['name'].value.replace(name_regexp,
                '$1' + form_id + '$2');
          }
        }

        // On renumérote aussi les tableaux internes. Ceci dépend
        // crucialement du fait que les form_id sont explorés dans
        // l'ordre croissant.
        var line_id = this.lineIdOf(form_id + 1);
        this.registerFormLine(line_id, line, form_id);
      }
      this.formset.removeChild(line);
      this.setTotalForms(this.getTotalForms() - 1);
    }
  }

  lineIdOf(position) {
    return this.form_ids[position];
  }

  updateDeleteButtons() {
    var buttons_state = !this.canDelete();
    for(var line_id in this.form_lines) {
      if(this.form_lines.hasOwnProperty(line_id)
        && this.form_lines[line_id].delete_button !== null) {
        this.form_lines[line_id].delete_button.disabled = buttons_state;
      }
    }
  }

  addDeleteButtons() {
    for(var form_id = 0; form_id < this.formset.children.length; form_id++) {
      var delete_button = document.createElement('button');
      var line_id = this.lineIdOf(form_id);
      this.form_lines[line_id].delete_button = delete_button;
      delete_button.attributes['name'] = this.inputName(form_id, 'DELETEBUTTON');
      delete_button.id = 'id-' + delete_button.attributes['name'];

      var delete_box = this.formset.children[form_id].querySelector('[name="' + this.inputName(form_id, 'DELETE') + '"]');
      delete_box.style.display = 'none';
      delete_box.type = 'hidden';

      delete_button.addEventListener('click', (function() {
        this.deleteLine(line_id);

        // On désactive les boutons de suppression si le formset
        // n'autorise plus aucune suppression.
        if(!this.canDelete()) {
          this.updateDeleteButtons();
        }

        // On réactive le bouton d'ajout si nécessaire.
        if(this.add_button !== null) {
          this.add_button.disabled = !this.canAdd();
        }
      }).bind(this));
      delete_box.parentNode.insertBefore(delete_button, delete_box);
    }
  }

  addAddButton() {
    var add_button = document.createElement('button');
    add_button.attributes['name'] = this.formset_prefix + '-ADDBUTTON';
    add_button.addEventListener('click', (function() {
      var old_can_delete = this.canDelete();
      this.addLine();

      // Après un ajout, on désactive le bouton d'ajout si le formset
      // est rempli.
      this.add_button.disabled = !this.canAdd();
      // Et on réactive les boutons de suppression si nécessaire.
      if(this.canDelete() && !old_can_delete) {
        this.updateDeleteButtons();
      }
    }).bind(this));
    this.add_button = add_button;
  }
}

document.addEventListener('DOMCOntentLoaded', function() {
  var formsets = document.getElementsByClassName('formset');
  for(var i = 0; i < formsets.length; i++) {
    formsets[i].formset = new DjangoFormset(formsets[i]);
  }
});

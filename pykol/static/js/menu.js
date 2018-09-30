function menu_toggle() {
  elt = $(this).parent();
  elt.siblings().removeClass("menu_current");
  elt.toggleClass("menu_current");
}

$(document).ready(function () {
  // Ajouter des règles CSS pour plier et déplier les menus
  var style = document.createElement("style");
  document.head.appendChild(style);
  var sheet = style.sheet;

  sheet.insertRule("nav > ul > li > *:first-child { cursor: pointer; }", 0);
  sheet.insertRule("nav > ul > li > ul { max-height: 0px; overflow: hidden; transition: max-height 0.25s ease; }", 0);
  sheet.insertRule("nav > ul > li.menu_current > ul { max-height: 1000px; transition: max-height 1s ease; }", 0);

  $("nav > ul > li > *:first-child").click(menu_toggle);

  // Ouverture du menu sur les petits écrans
  var menu = $("header > nav");
  $("#menu-button").click(function () { menu.toggle(); });
});

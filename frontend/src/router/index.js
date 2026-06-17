import { createRouter, createWebHistory } from "vue-router";
import TournamentList from "../views/TournamentList.vue";
import TournamentWorkspace from "../views/TournamentWorkspace.vue";
import Spielplan from "../views/Spielplan.vue";
import Sitzplan from "../views/Sitzplan.vue";
import Spielerverwaltung from "../views/Spielerverwaltung.vue";
import Konfiguration from "../views/Konfiguration.vue";
import Spielstand from "../views/Spielstand.vue";

const routes = [
  { path: "/", name: "tournaments", component: TournamentList },
  {
    path: "/tournaments/:id",
    component: TournamentWorkspace,
    props: true,
    children: [
      { path: "", redirect: (to) => `/tournaments/${to.params.id}/spielplan` },
      { path: "spielplan", name: "spielplan", component: Spielplan, props: true },
      { path: "sitzplan", name: "sitzplan", component: Sitzplan, props: true },
      { path: "spielerverwaltung", name: "spielerverwaltung", component: Spielerverwaltung, props: true },
      { path: "konfiguration", name: "konfiguration", component: Konfiguration, props: true },
      { path: "spielstand", name: "spielstand", component: Spielstand, props: true },
    ],
  },
];

export default createRouter({
  history: createWebHistory(),
  routes,
});

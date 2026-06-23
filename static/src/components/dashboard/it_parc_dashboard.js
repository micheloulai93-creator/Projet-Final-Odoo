/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, useState, onWillStart } from "@odoo/owl";

// Couleurs associées aux catégories d'équipement (cohérentes avec le SCSS)
const CATEGORY_COLORS = {
    poste_travail: "#2d6da8",
    serveur: "#6a3d9a",
    imprimante: "#e65100",
    reseau: "#00897b",
    telephone: "#ad7e00",
    autre: "#757575",
};

const CATEGORY_LABELS = {
    poste_travail: "Postes de travail",
    serveur: "Serveurs",
    imprimante: "Imprimantes",
    reseau: "Équip. réseau",
    telephone: "Téléphones IP",
    autre: "Autre",
};

export class ItParcDashboard extends Component {
    static template = "it_parc.Dashboard";

    setup() {
        this.orm = this.env.services.orm;
        this.action = this.env.services.action;

        this.state = useState({
            loading: true,
            // Vue d'ensemble du parc (Objectif 1 - Centralisation)
            nbEquipements: 0,
            nbAffectes: 0,
            nbMaintenance: 0,
            nbRetires: 0,
            nbDraft: 0,

            // Pilotage (Objectif 5 - vocabulaire exact du CDC)
            tauxImmobilisation: 0,
            coutTotalPossession: 0,
            valeurAchatTotale: 0,
            coutMaintenanceTotale: 0,
            nbFinDeVie: 0,

            // Anticipation (Objectif 3)
            nbAlertes: 0,
            nbGarantiesExpirantBientot: 0,
            nbContratsActifs: 0,
            nbContratsExpirantBientot: 0,

            // Graphiques
            chartData: [],
            categorieData: [],

            // Liste "à traiter"
            itemsUrgents: [],
        });

        onWillStart(async () => {
            await this.loadData();
        });
    }

    async loadData() {
        const [
            total,
            affectes,
            maintenance,
            retires,
            draft,
            nbAlertes,
            nbContratsActifs,
            nbContratsExpirantBientot,
        ] = await Promise.all([
            this.orm.searchCount("it.equipement", []),
            this.orm.searchCount("it.equipement", [["state", "=", "assigned"]]),
            this.orm.searchCount("it.equipement", [["state", "=", "in_maintenance"]]),
            this.orm.searchCount("it.equipement", [["state", "=", "retired"]]),
            this.orm.searchCount("it.equipement", [["state", "=", "draft"]]),
            this.orm.searchCount("it.alerte", [["state", "not in", ["traitee", "ignoree"]]]),
            this.orm.searchCount("it.contrat", [["state", "=", "actif"]]),
            this.orm.searchCount("it.contrat", [["state", "=", "actif"], ["is_expiring_soon", "=", true]]),
        ]);

        // Équipements : valeur d'achat, coût maintenance, garantie, catégorie, état
        const equipements = await this.orm.searchRead(
            "it.equipement",
            [],
            ["valeur_achat", "cout_total_maintenance", "categorie", "state", "garantie_expired", "jours_avant_garantie"]
        );

        const valeurAchatTotale = equipements.reduce((s, e) => s + (e.valeur_achat || 0), 0);
        const coutMaintenanceTotale = equipements.reduce((s, e) => s + (e.cout_total_maintenance || 0), 0);
        const coutTotalPossession = valeurAchatTotale + coutMaintenanceTotale;

        // Taux d'immobilisation = (en maintenance + retirés) / total
        const tauxImmobilisation = total > 0
            ? Math.round(((maintenance + retires) / total) * 100)
            : 0;

        // Équipements en fin de vie = garantie expirée ET pas encore retiré
        const nbFinDeVie = equipements.filter(
            (e) => e.garantie_expired && e.state !== "retired"
        ).length;

        // Garanties expirant dans les 30 prochains jours (et pas retirés)
        const nbGarantiesExpirantBientot = equipements.filter(
            (e) => e.state !== "retired" && e.jours_avant_garantie >= 0 && e.jours_avant_garantie <= 30
        ).length;

        // Répartition par catégorie
        const categorieData = this._buildCategorieData(equipements);

        const chartData = await this._loadChartData();
        const itemsUrgents = await this._loadItemsUrgents();

        Object.assign(this.state, {
            loading: false,
            nbEquipements: total,
            nbAffectes: affectes,
            nbMaintenance: maintenance,
            nbRetires: retires,
            nbDraft: draft,
            tauxImmobilisation,
            coutTotalPossession,
            valeurAchatTotale,
            coutMaintenanceTotale,
            nbFinDeVie,
            nbAlertes,
            nbGarantiesExpirantBientot,
            nbContratsActifs,
            nbContratsExpirantBientot,
            chartData,
            categorieData,
            itemsUrgents,
        });
    }

    _buildCategorieData(equipements) {
        const counts = {};
        for (const e of equipements) {
            const cat = e.categorie || "autre";
            counts[cat] = (counts[cat] || 0) + 1;
        }

        const total = equipements.length || 1;
        const order = ["poste_travail", "serveur", "imprimante", "reseau", "telephone", "autre"];

        // Construction des segments du donut (coordonnées cumulées en %)
        let cumulative = 0;
        const segments = [];
        for (const cat of order) {
            const count = counts[cat] || 0;
            if (count === 0) continue;
            const pct = (count / total) * 100;
            segments.push({
                categorie: cat,
                label: CATEGORY_LABELS[cat],
                color: CATEGORY_COLORS[cat],
                count,
                pct: Math.round(pct),
                offset: cumulative,
            });
            cumulative += pct;
        }
        return segments;
    }

    async _loadChartData() {
        const now = new Date();
        const months = [];
        for (let i = 5; i >= 0; i--) {
            const d = new Date(now.getFullYear(), now.getMonth() - i, 1);
            months.push({
                year: d.getFullYear(),
                month: d.getMonth(),
                label: d.toLocaleDateString("fr-FR", { month: "short" }),
            });
        }

        const rangeStart = new Date(months[0].year, months[0].month, 1);
        const rangeEnd = new Date(months[5].year, months[5].month + 1, 0, 23, 59, 59);
        const toOdooDatetime = (d) => d.toISOString().slice(0, 19).replace("T", " ");

        const interventions = await this.orm.searchRead(
            "it.intervention",
            [
                ["date_debut", ">=", toOdooDatetime(rangeStart)],
                ["date_debut", "<=", toOdooDatetime(rangeEnd)],
            ],
            ["date_debut", "cout"]
        );

        const values = months.map((m) => {
            return interventions
                .filter((rec) => {
                    const d = new Date(rec.date_debut.replace(" ", "T") + "Z");
                    return d.getUTCFullYear() === m.year && d.getUTCMonth() === m.month;
                })
                .reduce((sum, rec) => sum + (rec.cout || 0), 0);
        });

        const max = Math.max(...values, 1);
        const chartWidth = 560;
        const chartHeight = 180;
        const barGap = 16;
        const barWidth = (chartWidth - barGap * (values.length + 1)) / values.length;

        return values.map((value, idx) => {
            const barHeight = (value / max) * (chartHeight - 30);
            const x = barGap + idx * (barWidth + barGap);
            const y = chartHeight - barHeight - 20;
            return {
                label: months[idx].label,
                value: Math.round(value),
                x,
                y,
                width: barWidth,
                height: barHeight,
            };
        });
    }

    async _loadItemsUrgents() {
        // Top 5 alertes actives les plus urgentes (jours_restants croissant)
        const alertes = await this.orm.searchRead(
            "it.alerte",
            [["state", "not in", ["traitee", "ignoree"]]],
            ["name", "type_alerte", "jours_restants", "date_echeance"],
            { order: "jours_restants asc", limit: 5 }
        );

        return alertes.map((a) => ({
            id: a.id,
            label: a.name,
            type: a.type_alerte,
            joursRestants: a.jours_restants,
            urgent: a.jours_restants <= 7,
        }));
    }

    formatMontant(value) {
        return Math.round(value).toLocaleString("fr-FR");
    }

    openEquipements() {
        this.action.doAction("it_parc.action_it_equipement");
    }

    openEquipementsFiltres(state) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "it.equipement",
            views: [[false, "list"], [false, "form"]],
            domain: [["state", "=", state]],
            name: "Équipements",
        });
    }

    openAlertes() {
        this.action.doAction("it_parc.action_it_alerte");
    }

    openContrats() {
        this.action.doAction("it_parc.action_it_contrat");
    }

    openAlerte(alerteId) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "it.alerte",
            views: [[false, "form"]],
            res_id: alerteId,
        });
    }
}

registry.category("actions").add("it_parc_dashboard", ItParcDashboard);
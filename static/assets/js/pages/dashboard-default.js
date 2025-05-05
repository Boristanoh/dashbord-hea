'use strict';
// [ world-low chart ] start
(function () {
    var map = new jsVectorMap({
        selector: "#world-low",
        map: "world",
        markersSelectable: true,
        markers: [{
                coords: [-14.2350, -51.9253]
            },
            {
                coords: [35.8617, 104.1954]
            },
            {
                coords: [61, 105]
            },
            {
                coords: [26.8206, 30.8025]
            }
        ],
        markerStyle: {
            initial: {
                fill: '#3f4d67',

            },
            hover: {
                fill: '#04a9f5',
            },
        },
        markerLabelStyle: {
            initial: {
                fontFamily: "'Inter', sans-serif",
                fontSize: 13,
                fontWeight: 500,
                fill: '#3f4d67',
            },
        },
    });
})();
// [ world-low chart ] end
document.addEventListener("DOMContentLoaded", function () {
    // === BÉNÉFICE MENSUEL (courbe) ===
    const chartDiv = document.getElementById("Widget-line-chart");
    if (chartDiv) {
        const benefice = JSON.parse(chartDiv.dataset.benefice);
        const labels = JSON.parse(chartDiv.dataset.labels);

        const lineOptions = {
            chart: { type: 'line', height: 210, toolbar: { show: false } },
            dataLabels: { enabled: false },
            colors: ["#fff"],
            fill: { type: 'solid' },
            series: [{ name: "Bénéfice mensuel", data: benefice }],
            xaxis: {
                categories: labels,
                axisBorder: { show: false },
                axisTicks: { show: false },
                crosshairs: { show: false },
                labels: { style: { colors: "#fff" } }
            },
            yaxis: {
                axisBorder: { show: false },
                axisTicks: { show: false },
                crosshairs: { show: false },
                labels: { show: false }
            },
            grid: {
                padding: { bottom: 0, left: 10 },
                xaxis: { lines: { show: false } },
                yaxis: { lines: { show: false } }
            },
            markers: {
                size: 5,
                colors: '#fff',
                opacity: 0.9,
                strokeWidth: 2,
                hover: { size: 7 }
            },
            tooltip: {
                y: {
                    formatter: function (val) {
                        return new Intl.NumberFormat('fr-FR', {
                            style: 'currency',
                            currency: 'XOF',
                            minimumFractionDigits: 0
                        }).format(val);
                    }
                }
            }
        };

        const chart = new ApexCharts(chartDiv, lineOptions);
        chart.render();
    }

    // === CAMEMBERT ENTRÉES / SORTIES ===
    const pieDiv = document.getElementById("pie-chart");
    if (pieDiv) {
        const repartition = JSON.parse(pieDiv.dataset.repartition);
        const labels = Object.keys(repartition);
        let data = Object.values(repartition).map(val => parseFloat(val) || 0);  // sécurité

        const pieOptions = {
            chart: { type: 'pie', height: 350 },
            labels: labels,
            series: data,
            colors: ['#28a745', '#dc3545'],  // vert = entrées, rouge = sorties
            legend: { position: 'bottom' },
            tooltip: {
                y: {
                    formatter: function (val) {
                        return new Intl.NumberFormat('fr-FR', {
                            style: 'currency',
                            currency: 'XOF',
                            minimumFractionDigits: 0
                        }).format(val);
                    }
                }
            }
        };

        const pieChart = new ApexCharts(pieDiv, pieOptions);
        pieChart.render();
    }
});



// [ Widget-line-chart ] end
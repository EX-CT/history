import {useMemo} from 'react';
import {ActiveSpawnsQuery} from '../../lib/graphql';
import {Line} from 'react-chartjs-2';
import {Chart as ChartJS, Tooltip, LinearScale, LineElement, LineController, PointElement, CategoryScale, Filler, ChartOptions, Plugin, ScriptableContext} from 'chart.js';
import {useTheme} from '../../lib/useTheme';

ChartJS.register(Tooltip, LineController, LineElement, PointElement, LinearScale, Tooltip, CategoryScale, Filler);

const LABELS = ["-72h", "", "", "", "", "", "", "", "", "", "", "", "-60h", "", "", "", "", "", "", "", "", "", "", "", "-48h", "", "", "", "", "", "", "", "", "", "", "", "-36h", "", "", "", "", "", "", "", "", "", "", "", "-24h", "", "", "", "", "", "", "", "", "", "", "", "-12h", "", "", "", "", "", "", "", "", "", "", "now"];

export const Chart = ({influenceLogArray}: { influenceLogArray: ActiveSpawnsQuery['activeSpawns'][0]['influenceLogArray'] }) => {
  const theme = useTheme();
  const dark = theme === 'dark';

  const accent = dark ? '#2bb3df' : '#0e93c4';
  const grid = dark ? 'rgba(255,255,255,0.06)' : 'rgba(16,24,40,0.07)';
  const ticks = dark ? '#7c8696' : '#98a2b3';
  const crosshair = dark ? 'rgba(255,255,255,0.18)' : 'rgba(16,24,40,0.18)';
  const surface = dark ? '#1d212a' : '#ffffff';
  const border = dark ? '#272d38' : '#e3e7ee';
  const text = dark ? '#e6e9ef' : '#14171c';
  const muted = dark ? '#98a2b2' : '#5b6573';

  const crosshairPlugin = useMemo<Plugin<'line'>>(() => ({
    id: 'crosshair',
    afterDatasetsDraw: (chart) => {
      const active = chart.getActiveElements();
      if (!active.length) return;
      const {ctx, chartArea: {top, bottom}} = chart;
      const x = active[0].element.x;
      ctx.save();
      ctx.beginPath();
      ctx.moveTo(x, top);
      ctx.lineTo(x, bottom);
      ctx.lineWidth = 1;
      ctx.strokeStyle = crosshair;
      ctx.stroke();
      ctx.restore();
    },
  }), [crosshair]);

  const data = useMemo(() => ({
    labels: LABELS,
    datasets: [
      {
        label: "Influence",
        fill: true,
        backgroundColor: (ctx: ScriptableContext<'line'>) => {
          const {chart} = ctx;
          const {ctx: c, chartArea} = chart;
          if (!chartArea) return 'transparent';
          const g = c.createLinearGradient(0, chartArea.top, 0, chartArea.bottom);
          g.addColorStop(0, dark ? 'rgba(43,179,223,0.32)' : 'rgba(14,147,196,0.26)');
          g.addColorStop(1, dark ? 'rgba(43,179,223,0.01)' : 'rgba(14,147,196,0.01)');
          return g;
        },
        borderColor: accent,
        borderWidth: 2,
        pointRadius: 0,
        pointHoverRadius: 4,
        pointHoverBackgroundColor: accent,
        pointHoverBorderColor: surface,
        pointHoverBorderWidth: 2,
        data: influenceLogArray,
      },
    ],
  }), [influenceLogArray, accent, dark, surface]);

  const options = useMemo<ChartOptions<'line'>>(() => ({
    responsive: true,
    maintainAspectRatio: false,
    interaction: {mode: 'index', intersect: false},
    hover: {mode: 'index', intersect: false},
    plugins: {
      legend: {display: false},
      tooltip: {
        backgroundColor: surface,
        titleColor: muted,
        bodyColor: text,
        borderColor: border,
        borderWidth: 1,
        padding: 10,
        cornerRadius: 8,
        displayColors: false,
        titleFont: {size: 11, weight: 'normal'},
        bodyFont: {size: 13, weight: 'bold'},
        callbacks: {
          title: (items) => {
            const i = items[0]?.dataIndex ?? 0;
            const hoursAgo = 72 - i;
            return hoursAgo <= 0 ? 'Now' : `${hoursAgo}h ago`;
          },
          label: (ctx) => `Influence ${ctx.parsed.y}%`,
        },
      },
    },
    scales: {
      y: {
        min: 0,
        max: 100,
        ticks: {color: ticks, font: {size: 10}, stepSize: 25},
        grid: {color: grid},
        border: {display: false},
      },
      x: {
        ticks: {color: ticks, font: {size: 10}, maxRotation: 0, autoSkip: false},
        grid: {display: false},
        border: {color: grid},
      },
    },
    elements: {line: {tension: 0.25}},
    layout: {padding: {top: 6}},
  }), [grid, ticks, surface, muted, text, border]);

  return (
    <div style={{position: 'relative', height: 170}}>
      <Line data={data} options={options} plugins={[crosshairPlugin]}/>
    </div>
  );
};

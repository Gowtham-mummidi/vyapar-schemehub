import React, { useState, useEffect } from 'react';
import api from '../utils/api';
import { Bar, Doughnut } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
  ArcElement
} from 'chart.js';
import { IndianRupee, TrendingUp, ShieldCheck } from 'lucide-react';

ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
  ArcElement
);

const Analytics = () => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchAnalytics = async () => {
      try {
        setLoading(true);
        const res = await api.get('/recommendations/analytics');
        setData(res.data);
      } catch (err) {
        console.error('Failed to load analytics:', err);
      } finally {
        setLoading(false);
      }
    };
    fetchAnalytics();
  }, []);

  if (loading) {
     return (
       <div className="flex h-[400px] items-center justify-center">
         <div className="w-10 h-10 animate-spin rounded-full border-4 border-blue-600 border-t-transparent"></div>
       </div>
     );
  }

  const fundingDistribution = data?.funding_distribution || {
     Subsidy: 0, Grant: 0, Loan: 0, Equity: 0, Guarantee: 0
  };

  const doughnutData = {
    labels: Object.keys(fundingDistribution),
    datasets: [
      {
        data: Object.values(fundingDistribution),
        backgroundColor: [
          'rgba(37, 99, 235, 0.7)',
          'rgba(16, 185, 129, 0.7)',
          'rgba(99, 102, 241, 0.7)',
          'rgba(245, 158, 11, 0.7)',
          'rgba(239, 68, 68, 0.7)',
        ],
        borderColor: [
          '#2563eb',
          '#10b981',
          '#6366f1',
          '#f59e0b',
          '#ef4444',
        ],
        borderWidth: 1.5,
      },
    ],
  };

  const doughnutOptions = {
     responsive: true,
     maintainAspectRatio: false,
     plugins: {
        legend: {
           position: 'bottom',
           labels: {
              color: '#6b7280',
              font: { size: 11, weight: 'semibold' }
           }
        }
     }
  };

  const barData = {
    labels: ['Micro Limits', 'Small Limits', 'Medium Limits', 'Your Profile'],
    datasets: [
      {
        label: 'Financial Parameter Reference (Lakhs)',
        data: [500, 5000, 25000, (data?.total_potential_benefit || 0) / 100000],
        backgroundColor: 'rgba(99, 102, 241, 0.45)',
        borderColor: '#6366f1',
        borderWidth: 1.5,
      },
    ],
  };

  const barOptions = {
     responsive: true,
     maintainAspectRatio: false,
     plugins: {
        legend: { display: false }
     },
     scales: {
        y: {
           grid: { color: 'rgba(0, 0, 0, 0.05)' },
           ticks: { color: '#6b7280' }
        },
        x: {
           grid: { display: false },
           ticks: { color: '#6b7280' }
        }
     }
  };

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-lg font-bold text-gray-900">Analytics</h1>
        <p className="text-sm text-gray-500">Funding allocation, potential benefits, and eligibility overview.</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="card">
          <div className="card-body space-y-1">
            <div className="flex items-center gap-2 text-blue-600">
              <TrendingUp className="w-4 h-4" />
              <h4 className="text-xs font-bold uppercase tracking-wider text-gray-500">Eligibility Rate</h4>
            </div>
            <p className="text-2xl font-bold text-gray-900 mt-1">
              {data?.total_schemes_analyzed > 0 
                 ? `${Math.round((data.eligible_schemes_count / data.total_schemes_analyzed) * 100)}%` 
                 : '0%'}
            </p>
            <p className="text-xs text-gray-400">
              {data?.eligible_schemes_count} of {data?.total_schemes_analyzed} schemes
            </p>
          </div>
        </div>

        <div className="card">
          <div className="card-body space-y-1">
            <div className="flex items-center gap-2 text-green-600">
              <IndianRupee className="w-4 h-4" />
              <h4 className="text-xs font-bold uppercase tracking-wider text-gray-500">Potential Benefit</h4>
            </div>
            <p className="text-2xl font-bold text-gray-900 mt-1">
              ₹ {((data?.total_potential_benefit || 0) / 100000).toFixed(1)} Lakh
            </p>
            <p className="text-xs text-gray-400">
              Total from all qualified schemes
            </p>
          </div>
        </div>

        <div className="card">
          <div className="card-body space-y-1">
            <div className="flex items-center gap-2 text-indigo-600">
              <ShieldCheck className="w-4 h-4" />
              <h4 className="text-xs font-bold uppercase tracking-wider text-gray-500">Missing Docs</h4>
            </div>
            <p className="text-2xl font-bold text-gray-900 mt-1">
              {data?.critical_missing_documents?.length || 0}
            </p>
            <p className="text-xs text-gray-400">
              Pending registrations
            </p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="card">
          <div className="card-body">
            <h3 className="text-sm font-bold text-gray-900 mb-4">Schemes by Funding Type</h3>
            <div className="relative h-64">
              <Doughnut data={doughnutData} options={doughnutOptions} />
            </div>
          </div>
        </div>

        <div className="card">
          <div className="card-body">
            <h3 className="text-sm font-bold text-gray-900 mb-4">Turnover Scale (Lakhs)</h3>
            <div className="relative h-64">
              <Bar data={barData} options={barOptions} />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Analytics;

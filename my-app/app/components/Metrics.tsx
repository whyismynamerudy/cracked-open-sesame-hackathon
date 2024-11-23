"use client"
import React from 'react'
import styles from "../components/Metrics.module.css"

interface Metric {
    id: number
    title: string
    value: string|number
}

interface MetricsProps {
    metrics?: Metric[]
}

const Metrics: React.FC<MetricsProps> = ({ metrics }) => {
    const mockData: Metric[] = [
      { id: 1, title: 'Completion Rate', value: "0%" },
      { id: 2, title: 'Steps to completion', value: 20 },
      { id: 4, title: 'Error Rate', value: '0%' },
      { id: 3, title: 'Recommendation', value: 'We recommend you do this!' },
    ]

    const dataDisplayed = metrics || mockData

    return(
        <div className={styles.metricsContainer}>
      {dataDisplayed.map((metric) => (
        <div key={metric.id} className={styles.metricCard}>
          <h3 className={styles.metricTitle}>{metric.title}</h3>
          <p className={styles.metricValue}>{metric.value}</p>
        </div>
      ))}
        </div>
    )
}
export default Metrics

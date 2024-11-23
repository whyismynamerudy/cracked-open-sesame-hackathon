"use client"
import React, { useState, useEffect } from 'react'
import styles from "../components/Dashboard.module.css"
import { Bars } from 'react-loader-spinner'
import Metrics from './Metrics'

const Dashboard: React.FC = () => {
  const [loading, setLoading] = useState<boolean>(true)
  const [showStreaming, setShowStreaming] = useState<boolean>(true)

  useEffect(() => {
    setTimeout(() => {
      setLoading(false)
    }, 2000) 
  }, [])

  const handleToggle = () => {
    setShowStreaming((prev) => !prev) 
  }

  return (
    <div className={styles.dashboard}>
      <button className={styles.submit} onClick={handleToggle}>
        {showStreaming ? 
        <div>Hide Stream</div> : 'Load Stream'}
      </button>   
      {showStreaming ? 
        <div><Metrics/></div> : "Loading..."}  
      <div className="container">
        {loading ? (
          <div className={styles.loader}>
            <Bars
              height="80"
              width="80"
              color="#2C2C2C"
              wrapperStyle={{}}
              wrapperClass=""
              visible={true}
            />
          </div>
        ) : (
          <div className={styles.dataContainer}>
          </div>
        )}
      </div>
    </div>
  )
}

export default Dashboard

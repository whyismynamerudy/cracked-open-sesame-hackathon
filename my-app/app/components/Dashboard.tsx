"use client"
import React from 'react'
import styles from "../components/Dashboard.module.css"
import {Bars} from 'react-loader-spinner'

const Dashboard: React.FC = () => {

  return (
    <div className={styles.dashboard}>
        <div className='container'> 
        <Bars
        height="80"
        width="80"
        color="#2C2C2C"
        wrapperStyle={{}}
        wrapperClass=""
        visible={true}
      />
        </div>
    </div>
  )
}

export default Dashboard

"use client"
import React, { useState, useEffect } from 'react'
import styles from "../components/Form.module.css"

interface requestData {
    url: string
    intent: string
    context: string
}

const Form: React.FC = () => {

    const [requestData, setRequestData] = useState<requestData>({
        url: '',
        intent: '',
        context: ''
    })

    const [submitted, setSubmitted] = useState<boolean>(false)
    const [loading, setLoading] = useState<boolean>(false)
    const [error, setError] = useState<string | null>(null)

    const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const { name, value } = e.target

        setRequestData((prevData) => ({
            ...prevData,
            [name]: value
        }))
    }

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault()
    
        setLoading(true)
        setError(null)
    
        try {
            const response = await fetch('/api/submitform', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(requestData),
            })
    
            const result = await response.json()
    
            if (response.ok) {
                setSubmitted(true)
                setRequestData({ url: '', intent: '', context: '' }) 
            } else {
                setError(result.error || 'Unknown error')
            }
        } catch (error) {
            setError('Error occurred while submitting :(')
            console.error(error)  
        } finally {
            setLoading(false)
        }
    }
    
    useEffect(() => {
        if (submitted) {
            const timer = setTimeout(() => {
                setSubmitted(false)
            }, 2000)

            return () => clearTimeout(timer)
        }
    }, [submitted])

    return (
        <div className="sidebar">
            {submitted ? (
                <h2 className={styles.successMessage}>Form submitted successfully!</h2>
            ) : (
                <form onSubmit={handleSubmit} className="form">
                    <div className={styles.formGroup}>
                        <label> URL</label>
                        <input
                            type="text"
                            id="url"
                            name="url"
                            value={requestData.url}
                            onChange={handleChange}
                            required
                        />
                    </div>

                    <div className={styles.formGroup}>
                        <label>Intent</label>
                        <input
                            type="text"
                            id="intent"
                            name="intent"
                            value={requestData.intent}
                            onChange={handleChange}
                        />
                    </div>

                    <div className={styles.formGroup}>
                        <label>Context</label>
                        <input
                            type="text"
                            id="context"
                            name="context"
                            value={requestData.context}
                            onChange={handleChange}
                        />
                    </div>

                    <button className={styles.submitButton} type="submit" disabled={loading}>
                        {loading ? 'Submitting...' : 'Submit'}
                    </button>

                    {error && <p className={styles.errorMessage}>{error}</p>}
                </form>
            )}
        </div>
    )
}

export default Form

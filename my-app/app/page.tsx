import Form from "./components/Form";
import Dashboard from "./components/Dashboard";
import styles from "./components/Form.module.css";

export default function Home() {
  return (
    <div className={styles.pageContainer}>
      <div className={styles.sidebar}>
        <Form />
      </div>
      <div>
      <Dashboard/>
      </div>
    </div>
  )
}

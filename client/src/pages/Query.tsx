import Layout from "../components/layout/Layout";
import QueryInput from "../components/query/QueryInput";
import QueryResults from "../components/query/QueryResults";

export default function Query() {
  return (
    <Layout>
      <QueryInput />
      <QueryResults />
    </Layout>
  );
}

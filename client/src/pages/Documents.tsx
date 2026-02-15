import Layout from "../components/layout/Layout";
import DocumentList from "../components/documents/DocumentList";
import DocumentUpload from "../components/documents/DocumentUpload";

export default function Documents() {
  return (
    <Layout>
      <DocumentUpload />
      <DocumentList />
    </Layout>
  );
}

package blog.libraries.processors;

import java.util.ArrayList;
import java.util.List;
import javax.annotation.Generated;

@Generated(
    value = "org.mapstruct.ap.MappingProcessor"
)
public class ProductMapperImpl implements ProductMapper {

    @Override
    public ProductView create(ProductInput source) {
        if ( source == null ) {
            return null;
        }

        ProductView.ProductViewBuilder productView = ProductView.builder();

        productView.name( source.getName() );
        productView.count( source.getCount() );
        List<String> list = source.getTags();
        if ( list != null ) {
            productView.tags( new ArrayList<String>( list ) );
        }

        return productView.build();
    }

    @Override
    public void overwrite(ProductInput source, ProductView target) {
        if ( source == null ) {
            return;
        }

        target.setName( source.getName() );
        target.setCount( source.getCount() );
        if ( target.getTags() != null ) {
            List<String> list = source.getTags();
            if ( list != null ) {
                target.getTags().clear();
                target.getTags().addAll( list );
            }
            else {
                target.setTags( null );
            }
        }
        else {
            List<String> list = source.getTags();
            if ( list != null ) {
                target.setTags( new ArrayList<String>( list ) );
            }
        }
    }

    @Override
    public void patch(ProductInput source, ProductView target) {
        if ( source == null ) {
            return;
        }

        if ( source.getName() != null ) {
            target.setName( source.getName() );
        }
        if ( source.getCount() != null ) {
            target.setCount( source.getCount() );
        }
        if ( target.getTags() != null ) {
            List<String> list = source.getTags();
            if ( list != null ) {
                target.getTags().clear();
                target.getTags().addAll( list );
            }
        }
        else {
            List<String> list = source.getTags();
            if ( list != null ) {
                target.setTags( new ArrayList<String>( list ) );
            }
        }
    }
}
